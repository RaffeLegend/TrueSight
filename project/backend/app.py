from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from detector import is_ai_generated
from werkzeug.utils import secure_filename
import traceback
import os

# 初始化 Flask 应用
app = Flask(__name__)
CORS(app)  # 允许跨域访问，方便前端从本地文件或其他端口访问

# 设置上传目录
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # 自动创建 uploads 文件夹

@app.route('/')
def home():
    return render_template('index.html')
    # return jsonify({"message": "AI 图像检测后端正在运行。"})

@app.route('/ping')
def ping():
    return "pong"

@app.route('/api/detect', methods=['POST'])
def detect_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image file selected.'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        print('image_path: ', filepath, flush=True)
        result = is_ai_generated(filepath)
        print('Result:', result, flush=True)

        # **只加 200，不改数据**
        return jsonify(result), 200
    except Exception as e:
        print("Detection Error:", e, flush=True)
        traceback.print_exc()
        return jsonify({'error': 'Server detection failed.'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # app.run(debug=True)
    print(f"Flask server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
