from flask import Flask, send_from_directory,send_file, jsonify, request, after_this_request, Response
from flask_cors import CORS
import os
import uuid
import librosa
import soundfile as sf
from PIL import Image
import numpy as np
import time
import ciphertext_retrial
from ciphertext_retrial import img2audio_retrial, audio2img_retrial, text2img_audio_retrial, audio_text2img_retrial, audio_img2img_retrial
from image_text_audio_encrypt_code.image_text_audio_en_de import encrypt_audio, encrypt_image
from collections import defaultdict
import json

img_database = "dataset/MSCOCO_origin/train2017"
audio_database = "dataset/ESC-50_classified/audio_database"
encrypted_audio_database = "image_text_audio_encrypt_code"
encrypted_img_database = "image_text_audio_encrypt_code"
# img_database = "pre_show"
# audio_database = "pre_show"

# 创建 Flask 应用实例
app = Flask(__name__)
# 允许所有来源的跨域请求，并支持凭证
CORS(app)

# 定义上传文件夹路径
UPLOAD_FOLDER = 'uploads'
# 如果上传文件夹不存在，则创建
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# 定义添加响应头的装饰器函数

def add_cors_headers(func_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            @after_this_request
            def add_header(response):
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
                response.headers['Access-Control-Allow-Credentials'] = 'true'
                response.headers['X-Content-Type-Options'] = 'nosniff'
                return response
            return func(*args, **kwargs)
        wrapper.__name__ = f"{func_name}_wrapper"
        return wrapper
    return decorator


# model1部分
# 定义上传图片的路由 (model1)
@app.route('/api/upload_image', methods=['POST'])
@add_cors_headers('upload_image')
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        try:
            def generate():
                # 使用生成器实时返回处理过程
                model1_generator = img2audio_retrial(file_path)
                while True:
                    try:
                        log = next(model1_generator)
                        yield f"data: {log.decode('utf-8')}\n\n"
                    except StopIteration as e:
                        origin_audio_path = f"{audio_database}/{e.value}"
                        encrypt_audio_path = f"encrypt_{e.value}"
                        encrypt_audio(origin_audio_path, f"{encrypted_audio_database}/"+encrypt_audio_path)
                        encrypted_audio, decrypted_audio = encrypt_audio_path,e.value
                        yield f"data: AUDIO_READY:{encrypted_audio}:{decrypted_audio}\n\n"
                        break
            
            return Response(generate(), mimetype='text/event-stream')
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": str(e)}), 500


# 定义下载解密音乐文件的路由 (model1)
@app.route('/get_music/<filename>')
@add_cors_headers('download_music')
def download_music(filename):
    try:
        return send_from_directory(audio_database, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# 定义下载加密音乐文件的路由 (model1)
@app.route('/get_music_encrypt/<filename>')
@add_cors_headers('download_music_encrypt')
def download_music_encrypt(filename):
    try:
        return send_from_directory(encrypted_audio_database, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404



# model2部分
# 定义上传音频的路由 (model2)
@app.route('/api/upload_audio', methods=['POST'])
@add_cors_headers('upload_audio')
def upload_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = str(uuid.uuid4()) + os.path.splitext(file.filename)[1]
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        try:
            def generate():
                # 使用生成器实时返回处理过程
                model2_generator = audio2img_retrial(file_path)
                while True:
                    try:
                        log = next(model2_generator)
                        yield f"data: {log.decode('utf-8')}\n\n"
                    except StopIteration as e:
                        origin_image_path = f"{img_database}/{e.value}"
                        encrypt_image_path = f"encrypt_{e.value}"
                        encrypt_image(origin_image_path, f"{encrypted_img_database}/" + encrypt_image_path)
                        encrypted_image, decrypted_image = encrypt_image_path, e.value
                        yield f"data: IMAGE_READY:{encrypted_image}:{decrypted_image}\n\n"
                        break
            
            return Response(generate(), mimetype='text/event-stream')
            
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"error": str(e)}), 500


# 定义下载解密图片文件的路由 (model2, model3, model4)
@app.route('/image/<filename>')
@add_cors_headers('download_image')
def download_image(filename):
    try:
        return send_from_directory(img_database, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# 定义下载加密图片文件的路由 (model2, model3, model4)
@app.route('/image_encrypt/<filename>')
@add_cors_headers('download_encrypted_image')
def download_encrypted_image(filename):
    try:
        return send_from_directory(encrypted_img_database, filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404


# 定义处理文本输入的路由 (model3)
@app.route('/api/get_text_results', methods=['POST'])
@add_cors_headers('get_text_results')
def get_text_results():
    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({"error": "Text input is required"}), 400

        def generate():
            # 使用生成器实时返回处理过程
            model3_generator = text2img_audio_retrial(text)
            while True:
                try:
                    log = next(model3_generator)
                    yield f"data: {log.decode('utf-8')}\n\n"
                except StopIteration as e:
                    origin_audio_path = f"{audio_database}/{e.value[1]}"
                    encrypt_audio_path = f"encrypt_{e.value[1]}"
                    encrypt_audio(origin_audio_path, f"{encrypted_audio_database}/" + encrypt_audio_path)

                    origin_image_path = f"{img_database}/{e.value[0]}"
                    encrypt_image_path = f"encrypt_{e.value[0]}"
                    encrypt_image(origin_image_path, f"{encrypted_img_database}/" + encrypt_image_path)


                    encrypted_image, decrypted_image, encrypted_audio, decrypted_audio = encrypt_image_path, e.value[0], encrypt_audio_path, e.value[1]
                    yield f"data: IMAGE_AUDIO_READY:{encrypted_image}:{decrypted_image}:{encrypted_audio}:{decrypted_audio}\n\n"
                    break

        return Response(generate(), mimetype='text/event-stream')

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# model4部分
# 定义上传文件的路由 (model4)
@app.route('/upload_t_a', methods=['POST'])
@add_cors_headers('upload_text_audio')
def upload_text_audio():
    if 'audio' not in request.files or 'text' not in request.form:
        return jsonify({"error": "No file part"}), 400

    audio = request.files['audio']
    text = request.form['text']

    if audio.filename == '' or text.strip() == '':
        return jsonify({"error": "No selected file or text"}), 400

    audio_path = os.path.join(UPLOAD_FOLDER, audio.filename)

    if audio:
        audio.save(audio_path)

    try:
        def generate():
            # 使用生成器实时返回处理过程
            model4_generator = audio_text2img_retrial(audio_path,text)
            while True:
                try:
                    log = next(model4_generator)
                    yield f"data: {log.decode('utf-8')}\n\n"
                except StopIteration as e:
                    origin_image_path = f"{img_database}/{e.value}"
                    encrypt_image_path = f"encrypt_{e.value}"
                    encrypt_image(origin_image_path, f"{encrypted_img_database}/" + encrypt_image_path)
                    encrypted_image, decrypted_image = encrypt_image_path, e.value
                    yield f"data: IMAGE_READY:{encrypted_image}:{decrypted_image}\n\n"
                    break
        
        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        os.remove(audio_path)  # 删除上传的音频文件
        return jsonify({"error": str(e)}), 500

# model5部分
# 定义上传文件的路由 (model5)
@app.route('/upload', methods=['POST'])
@add_cors_headers('upload_files')
def upload_files():
    if 'image' not in request.files or 'audio' not in request.files:
        return jsonify({"error": "No file part"}), 400

    image = request.files['image']
    audio = request.files['audio']

    if image.filename == '' or audio.filename == '':
        return jsonify({"error": "No selected file"}), 400

    image_path = os.path.join(UPLOAD_FOLDER, image.filename)
    audio_path = os.path.join(UPLOAD_FOLDER, audio.filename)

    if image:
        image.save(image_path)
    if audio:
        audio.save(audio_path)

    try:
        def generate():
            # 使用生成器实时返回处理过程
            model5_generator = audio_img2img_retrial(audio_path,image_path)
            while True:
                try:
                    log = next(model5_generator)
                    yield f"data: {log.decode('utf-8')}\n\n"
                except StopIteration as e:
                    origin_image_path = f"{img_database}/{e.value}"
                    encrypt_image_path = f"encrypt_{e.value}"
                    encrypt_image(origin_image_path, f"{encrypted_img_database}/" + encrypt_image_path)
                    encrypted_image, decrypted_image = encrypt_image_path, e.value
                    yield f"data: IMAGE_READY:{encrypted_image}:{decrypted_image}\n\n"
                    break
        
        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        os.remove(image_path)  # 删除上传的图片文件
        os.remove(audio_path)  # 删除上传的音频文件
        return jsonify({"error": str(e)}), 500

# 添加获取文件列表的路由
@app.route('/api/files', methods=['GET'])
@add_cors_headers('get_files')
def get_files():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 30))
        sort_by = request.args.get('sort_by', 'name')
        sort_order = request.args.get('sort_order', 'asc')
        file_type = request.args.get('type', 'all')
        
        print(f"Getting files: type={file_type}, page={page}, sort_by={sort_by}")
        
        # 检查并创建加密目录
        if not os.path.exists(encrypted_audio_database):
            os.makedirs(encrypted_audio_database)
        if not os.path.exists(encrypted_img_database):
            os.makedirs(encrypted_img_database)
        
        # 获取所有文件列表
        all_files = []
        if file_type in ['all', 'image']:
            img_files = [f for f in os.listdir(img_database) 
                        if os.path.isfile(os.path.join(img_database, f))]
            for img in img_files:
                stats = os.stat(os.path.join(img_database, img))
                all_files.append({
                    'id': img,
                    'name': img,
                    'type': 'image',
                    'size': stats.st_size,
                    'date': stats.st_mtime,
                    'path': f"/image/{img}",
                    'encrypted_path': f"/image_encrypt/encrypt_{img}"
                })
        
        if file_type in ['all', 'audio']:
            audio_files = [f for f in os.listdir(audio_database) 
                          if os.path.isfile(os.path.join(audio_database, f))]
            for audio in audio_files:
                stats = os.stat(os.path.join(audio_database, audio))
                all_files.append({
                    'id': audio,
                    'name': audio,
                    'type': 'audio',
                    'size': stats.st_size,
                    'date': stats.st_mtime,
                    'path': f"/get_music/{audio}",
                    'encrypted_path': f"/get_music_encrypt/encrypt_{audio}"
                })

        # 排序
        reverse = sort_order == 'desc'
        if sort_by == 'size':
            all_files.sort(key=lambda x: x['size'], reverse=reverse)
        elif sort_by == 'date':
            all_files.sort(key=lambda x: x['date'], reverse=reverse)
        else:  # sort by name
            all_files.sort(key=lambda x: x['name'], reverse=reverse)
        
        # 分页
        total = len(all_files)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        page_files = all_files[start:end]
        
        # 只处理当前页的文件加密
        files_to_return = []
        for file in page_files:
            try:
                if file['type'] == 'image':
                    original_path = os.path.join(img_database, file['name'])
                    encrypted_path = os.path.join(encrypted_img_database, f"encrypt_{file['name']}")
                    if not os.path.exists(encrypted_path):
                        encrypt_image(original_path, encrypted_path)
                        print(f"Created encrypted image: {encrypted_path}")
                else:
                    original_path = os.path.join(audio_database, file['name'])
                    encrypted_path = os.path.join(encrypted_audio_database, f"encrypt_{file['name']}")
                    if not os.path.exists(encrypted_path):
                        encrypt_audio(original_path, encrypted_path)
                        print(f"Created encrypted audio: {encrypted_path}")
                
                files_to_return.append(file)
            except Exception as e:
                print(f"Error processing file {file['name']}: {str(e)}")
                continue
        
        print(f"Returning {len(files_to_return)} files, page {page} of {total_pages}")
        return jsonify({
            'files': files_to_return,
            'total': total,
            'total_pages': total_pages,
            'current_page': page
        })
    except Exception as e:
        print(f"Error in get_files: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 添加文件预览/加密获取路由
@app.route('/api/preview/<path:filename>')
@add_cors_headers('preview_file')
def preview_file(filename):
    # 判断文件类型
    is_audio = any(filename.lower().endswith(ext) for ext in ['.mp3', '.wav', '.ogg'])
    
    if is_audio:
        origin_path = os.path.join(audio_database, filename)
        encrypted_path = f"{encrypted_audio_database}/encrypt_{filename}"
        if not os.path.exists(encrypted_path):
            encrypt_audio(origin_path, encrypted_path)
    else:
        origin_path = os.path.join(img_database, filename)
        encrypted_path = f"{encrypted_img_database}/encrypt_{filename}"
        if not os.path.exists(encrypted_path):
            encrypt_image(origin_path, encrypted_path)
            
    return jsonify({
        'original': f"/{'get_music' if is_audio else 'image'}/{filename}",
        'encrypted': f"/{'get_music_encrypt' if is_audio else 'image_encrypt'}/encrypt_{filename}"
    })

# 定义主页路由
@app.route('/')
@add_cors_headers('index')
def index():
    # 发送 'frontend.html' 文件
    return send_from_directory('.', 'frontend.html')


# 启动 Flask 应用
if __name__ == '__main__':
    app.run(debug=True, port=5000)