from flask import Flask, render_template, request, jsonify
import os
import requests
from PIL import Image
import imagehash
from io import BytesIO

app = Flask(__name__)

# 图片存储目录
WORKING_DIR = os.path.join(os.path.dirname(__file__), 'working')
os.makedirs(WORKING_DIR, exist_ok=True)

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
                            'hash_diff': diff
                        })
                except Exception as e:
                    continue
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return jsonify({
            'success': True,
            'is_duplicate': len(matches) > 0,
            'target_hash': str(target_hash),
            'matches': matches,
            'total_images': len(working_files),
            'message': f'发现 {len(matches)} 个相似图片' if matches else '未找到重复图片'
        })
        
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
                images.append({
                    'filename': fname,
                    'hash': str(img_hash),
                    'size': os.path.getsize(fpath),
                    'width': img.width,
                    'height': img.height
                })
            except:
                images.append({
                    'filename': fname,
                    'hash': None,
                    'size': os.path.getsize(fpath)
                })
    
    return jsonify({
        'success': True,
        'images': images,
        'count': len(images)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
