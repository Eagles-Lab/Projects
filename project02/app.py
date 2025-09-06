from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import cv2
import numpy as np
import json
import base64
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# 加载人脸检测器和识别器
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
face_recognizer = cv2.face.LBPHFaceRecognizer_create()

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['WTF_CSRF_ENABLED'] = False

# 创建必要的目录
USERS_DB_FILE = 'users.json'
FACE_ENCODINGS_DIR = 'face_encodings'
os.makedirs(FACE_ENCODINGS_DIR, exist_ok=True)

# 初始化用户数据库
def init_users_db():
    if not os.path.exists(USERS_DB_FILE):
        with open(USERS_DB_FILE, 'w') as f:
            json.dump([], f)

# 获取所有用户
def get_users():
    with open(USERS_DB_FILE, 'r') as f:
        return json.load(f)

# 保存用户
def save_users(users):
    with open(USERS_DB_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# 根据用户名查找用户
def find_user_by_username(username):
    users = get_users()
    for user in users:
        if user['username'] == username:
            return user
    return None

# 保存人脸特征
def save_face_features(username, face_image):
    try:
        # 转换为灰度图
        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        
        # 检测人脸
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            return False, "未检测到人脸"
        
        if len(faces) > 1:
            return False, "检测到多个人脸，请确保图像中只有一个人脸"
        
        # 获取人脸区域
        x, y, w, h = faces[0]
        face_roi = gray[y:y+h, x:x+w]
        
        # 调整大小为统一尺寸
        face_roi = cv2.resize(face_roi, (100, 100))
        
        # 保存人脸特征
        feature_file = os.path.join(FACE_ENCODINGS_DIR, f"{username}.npy")
        np.save(feature_file, face_roi)
        
        return True, None
    except Exception as e:
        return False, f"处理图像时出错: {str(e)}"

# 获取人脸特征
def get_face_features(username):
    feature_file = os.path.join(FACE_ENCODINGS_DIR, f"{username}.npy")
    if os.path.exists(feature_file):
        return np.load(feature_file)
    return None

# 处理图像并提取人脸特征
def process_face_image(base64_image):
    try:
        # 解码Base64图像
        header, encoded = base64_image.split(",", 1)
        binary_data = base64.b64decode(encoded)
        
        # 将二进制数据转换为图像
        nparr = np.frombuffer(binary_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return img, None
    except Exception as e:
        return None, f"处理图像时出错: {str(e)}"

# 初始化应用
init_users_db()

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        face_image = data.get('face_image')
        
        # 验证输入
        if not username or not password or not face_image:
            return jsonify({'success': False, 'message': '所有字段都是必填的'}), 400
        
        # 检查用户名是否已存在
        if find_user_by_username(username):
            return jsonify({'success': False, 'message': '用户名已存在'}), 400
        
        # 处理人脸图像
        face_image, error = process_face_image(face_image)
        if error:
            return jsonify({'success': False, 'message': error}), 400
            
        # 保存人脸特征
        success, error = save_face_features(username, face_image)
        if not success:
            return jsonify({'success': False, 'message': error}), 400
        
        # 创建新用户
        new_user = {
            'username': username,
            'password': generate_password_hash(password),
            'created_at': datetime.now().isoformat()
        }
        
        # 保存用户信息
        users = get_users()
        users.append(new_user)
        save_users(users)
        
        return jsonify({'success': True, 'message': '注册成功'})
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        login_type = data.get('login_type', 'password')
        
        if login_type == 'password':
            username = data.get('username')
            password = data.get('password')
            
            # 验证输入
            if not username or not password:
                return jsonify({'success': False, 'message': '用户名和密码都是必填的'}), 400
            
            # 查找用户
            user = find_user_by_username(username)
            if not user or not check_password_hash(user['password'], password):
                return jsonify({'success': False, 'message': '用户名或密码不正确'}), 401
            
            # 登录成功
            session['username'] = username
            return jsonify({'success': True, 'message': '登录成功'})
        
        elif login_type == 'face':
            username = data.get('username')
            face_image = data.get('face_image')
            
            # 验证输入
            if not username or not face_image:
                return jsonify({'success': False, 'message': '用户名和人脸图像都是必填的'}), 400
            
            # 查找用户
            user = find_user_by_username(username)
            if not user:
                return jsonify({'success': False, 'message': '用户不存在'}), 401
            
            # 获取存储的人脸特征
            stored_features = get_face_features(username)
            if stored_features is None:
                return jsonify({'success': False, 'message': '未找到用户的人脸数据'}), 401
            
            # 处理上传的人脸图像
            face_image, error = process_face_image(face_image)
            if error:
                return jsonify({'success': False, 'message': error}), 400
                
            # 转换为灰度图
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
            
            # 检测人脸
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                return jsonify({'success': False, 'message': '未检测到人脸'}), 400
            
            if len(faces) > 1:
                return jsonify({'success': False, 'message': '检测到多个人脸，请确保图像中只有一个人脸'}), 400
            
            # 获取人脸区域
            x, y, w, h = faces[0]
            face_roi = gray[y:y+h, x:x+w]
            
            # 调整大小为统一尺寸
            face_roi = cv2.resize(face_roi, (100, 100))
            
            # 计算两个人脸特征之间的差异
            diff = np.mean(np.abs(face_roi - stored_features))
            
            # 设置阈值（可以根据需要调整）
            print(diff)
            if diff > 500:  # 差异过大，认为不是同一个人
                return jsonify({'success': False, 'message': '人脸识别失败，请尝试其他登录方式'}), 401
            
            # 登录成功
            session['username'] = username
            return jsonify({'success': True, 'message': '人脸识别登录成功'})
        
        else:
            return jsonify({'success': False, 'message': '不支持的登录类型'}), 400
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    return render_template('dashboard.html', username=username)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)