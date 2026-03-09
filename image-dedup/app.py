from flask import Flask, render_template, request, jsonify
import os
import requests
from PIL import Image
import imagehash
from io import BytesIO
import json

app = Flask(__name__)

# 图片存储目录
WORKING_DIR = os.path.join(os.path.dirname(__file__), 'working')
os.makedirs(WORKING_DIR, exist_ok=True)

# 加载 SKU 数据库
DB_INDEX_PATH = '/home/ken/working/图片查重/db_index.json'
sku_database = {}

def load_sku_database():
    """加载 SKU 数据库，建立 phash → SKU 的映射"""
    global sku_database
    try:
        with open(DB_INDEX_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            filename = item.get('filename', '')
            sku = item.get('sku', '')
            phash = item.get('phash', '')
            if phash and sku:
                sku_database[phash] = {
                    'sku': sku,
                    'filename': filename
                }
        print(f"✅ SKU 数据库加载完成，共 {len(sku_database)} 条记录")
    except Exception as e:
        print(f"⚠️ 加载 SKU 数据库失败: {e}")

# 启动时加载数据库
load_sku_database()

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/api/check', methods=['POST'])
def check_image():
    """检查图片是否重复"""
    data = request.get_json()
    image_url = data.get('url')
    
    if not image_url:
        return jsonify({'error': '请提供图片链接'}), 400
    
    try:
        # 下载图片
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
        }
        response = requests.get(image_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # 打开图片
        img = Image.open(BytesIO(response.content))
        
        # 转换为 RGB（处理各种格式）
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 计算感知哈希
        target_hash = imagehash.phash(img)
        target_hash_str = str(target_hash)
        
        # 扫描 working 目录
        matches = []
        working_files = []
        
        for fname in os.listdir(WORKING_DIR):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
                fpath = os.path.join(WORKING_DIR, fname)
                try:
                    existing = Image.open(fpath)
                    if existing.mode in ('RGBA', 'P'):
                        existing = existing.convert('RGB')
                    
                    existing_hash = imagehash.phash(existing)
                    diff = target_hash - existing_hash
                    
                    working_files.append({
                        'name': fname,
                        'hash': str(existing_hash),
                        'diff': diff
                    })
                    
                    if diff <= 8:  # 相似度阈值（越小越严格）
                        matches.append({
                            'filename': fname,
                            'similarity': max(0, 100 - diff * 12.5),  # 转换为百分比
                            'hash_diff': diff,
                            'hash': str(existing_hash)
                        })
                except Exception as e:
                    continue
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        # 为每个匹配查找 SKU
        for match in matches:
            match_hash = match['hash']
            # 精确匹配
            if match_hash in sku_database:
                match['sku'] = sku_database[match_hash]['sku']
                match['db_filename'] = sku_database[match_hash]['filename']
            else:
                match['sku'] = 'UNKNOWN'
                match['db_filename'] = None
        
        # 构建输出结果
        result = {
            'success': True,
            'is_duplicate': len(matches) > 0,
            'target_hash': target_hash_str,
            'matches': matches,
            'total_images': len(working_files),
            'message': f'发现 {len(matches)} 个相似图片' if matches else '未找到重复图片'
        }
        
        # 如果找到重复，输出具体的 SKU 列表
        if matches:
            sku_list = [m['sku'] for m in matches if m.get('sku') and m['sku'] != 'UNKNOWN']
            result['duplicate_skus'] = sku_list
            result['duplicate_count'] = len(sku_list)
        
        return jsonify(result)
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'下载图片失败: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'处理失败: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """上传图片到 working 目录"""
    if 'image' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': '文件名不能为空'}), 400
    
    try:
        filename = file.filename
        filepath = os.path.join(WORKING_DIR, filename)
        file.save(filepath)
        
        # 计算哈希
        img = Image.open(filepath)
        img_hash = imagehash.phash(img)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'hash': str(img_hash),
            'message': f'图片 {filename} 已保存'
        })
    except Exception as e:
        return jsonify({'error': f'上传失败: {str(e)}'}), 500

@app.route('/api/images', methods=['GET'])
def list_images():
    """列出 working 目录中的所有图片"""
    images = []
    for fname in os.listdir(WORKING_DIR):
        if fname.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')):
            fpath = os.path.join(WORKING_DIR, fname)
            try:
                img = Image.open(fpath)
                img_hash = imagehash.phash(img)
                hash_str = str(img_hash)
                
                # 查找 SKU
                sku_info = sku_database.get(hash_str, {})
                
                images.append({
                    'filename': fname,
                    'hash': hash_str,
                    'size': os.path.getsize(fpath),
                    'width': img.width,
                    'height': img.height,
                    'sku': sku_info.get('sku', 'UNKNOWN')
                })
            except:
                images.append({
                    'filename': fname,
                    'hash': None,
                    'size': os.path.getsize(fpath),
                    'sku': 'UNKNOWN'
                })
    
    return jsonify({
        'success': True,
        'images': images,
        'count': len(images)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
