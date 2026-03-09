# 图片查重工具

基于 Flask + imagehash 的图片查重服务，可部署到 Render。

## 功能

- 🔗 **链接查重**：输入图片 URL，检查是否与库中图片重复
- 📤 **本地上传**：拖拽或点击上传图片
- 📁 **图片库管理**：查看已上传的图片及其哈希值
- 🎯 **感知哈希**：使用 pHash 算法，检测相似图片（非完全匹配也能发现）

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python app.py
```

访问 http://localhost:5000

## 部署到 Render

### 方法一：使用 Render Blueprint（推荐）

1. Fork 这个仓库到你的 GitHub
2. 登录 [Render](https://render.com)
3. 点击 "New +" → "Blueprint"
4. 选择你的仓库
5. 点击 "Apply" 完成部署

### 方法二：手动创建

1. 创建新的 Web Service
2. 选择 Python 环境
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`
5. 添加 Disk：
   - Name: `working-images`
   - Mount Path: `/opt/render/project/src/working`
   - Size: 1GB

## API

### 检查图片
```bash
POST /api/check
Content-Type: application/json

{"url": "https://example.com/image.jpg"}
```

### 上传图片
```bash
POST /api/upload
Content-Type: multipart/form-data

image: [file]
```

### 获取图片列表
```bash
GET /api/images
```

## 技术栈

- **后端**: Flask + Gunicorn
- **图像处理**: Pillow + imagehash
- **部署**: Render (免费)
- **算法**: Perceptual Hash (pHash)

## 相似度阈值

- `diff <= 8`: 认为是相似图片
- `diff = 0`: 完全相同的图片
- 阈值越小越严格
