from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 创建必要的目录
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 数据存储（在实际应用中应使用数据库）
USERS_FILE = 'data/users.json'
BOOKS_FILE = 'data/books.json'
ORDERS_FILE = 'data/orders.json'

os.makedirs('data', exist_ok=True)

# 初始化数据文件
def initialize_data_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(BOOKS_FILE):
        with open(BOOKS_FILE, 'w') as f:
            json.dump([], f)
    
    if not os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'w') as f:
            json.dump([], f)

initialize_data_files()

# 辅助函数
def load_data(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def save_data(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

# 路由
@app.route('/')
def index():
    books = load_data(BOOKS_FILE)
    return render_template('index.html', books=books)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        users = load_data(USERS_FILE)
        
        # 检查用户名是否已存在
        if any(user['username'] == username for user in users):
            flash('用户名已存在')
            return redirect(url_for('register'))
        
        # 创建新用户
        new_user = {
            'id': len(users) + 1,
            'username': username,
            'password': password,  # 实际应用中应加密
            'email': email,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        users.append(new_user)
        save_data(users, USERS_FILE)
        
        flash('注册成功，请登录')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = load_data(USERS_FILE)
        # 验证用户
        user = next((user for user in users if user['username'] == username and user['password'] == password), None)
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('登录成功')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('已退出登录')
    return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_book():
    if 'user_id' not in session:
        flash('请先登录')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        description = request.form['description']
        price = float(request.form['price'])
        condition = request.form['condition']
        
        # 处理图片上传
        book_image = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                # 获取原始文件扩展名
                original_filename = file.filename
                file_ext = os.path.splitext(original_filename)[1]
                if not file_ext:
                    file_ext = '.png'  # 默认扩展名
                
                # 生成带时间戳的唯一文件名
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                safe_filename = secure_filename(os.path.splitext(original_filename)[0]) or 'image'
                new_filename = f"{safe_filename}_{timestamp}{file_ext}"
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                file.save(file_path)
                # 使用url_for生成正确的静态文件URL路径
                book_image = '/' + file_path
        
        books = load_data(BOOKS_FILE)
        
        # 创建新书籍
        new_book = {
            'id': len(books) + 1,
            'title': title,
            'author': author,
            'description': description,
            'price': price,
            'condition': condition,
            'image': book_image,
            'seller_id': session['user_id'],
            'seller_name': session['username'],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'available'
        }
        
        books.append(new_book)
        save_data(books, BOOKS_FILE)
        
        flash('书籍上传成功')
        return redirect(url_for('index'))
    
    return render_template('upload.html')

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    books = load_data(BOOKS_FILE)
    book = next((book for book in books if book['id'] == book_id), None)
    
    if not book:
        flash('书籍不存在')
        return redirect(url_for('index'))
    
    return render_template('book_detail.html', book=book)

@app.route('/order/<int:book_id>', methods=['GET', 'POST'])
def place_order(book_id):
    if 'user_id' not in session:
        flash('请先登录')
        return redirect(url_for('login'))
    
    books = load_data(BOOKS_FILE)
    book = next((book for book in books if book['id'] == book_id), None)
    
    if not book:
        flash('书籍不存在')
        return redirect(url_for('index'))
    
    if book['status'] != 'available':
        flash('该书籍已售出')
        return redirect(url_for('index'))
    
    if book['seller_id'] == session['user_id']:
        flash('不能购买自己上传的书籍')
        return redirect(url_for('book_detail', book_id=book_id))
    
    if request.method == 'POST':
        address = request.form['address']
        phone = request.form['phone']
        
        orders = load_data(ORDERS_FILE)
        
        # 创建新订单
        new_order = {
            'id': len(orders) + 1,
            'book_id': book_id,
            'book_title': book['title'],
            'seller_id': book['seller_id'],
            'seller_name': book['seller_name'],
            'buyer_id': session['user_id'],
            'buyer_name': session['username'],
            'price': book['price'],
            'address': address,
            'phone': phone,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'pending'
        }
        
        orders.append(new_order)
        save_data(orders, ORDERS_FILE)
        
        # 更新书籍状态
        book['status'] = 'sold'
        save_data(books, BOOKS_FILE)
        
        flash('订单提交成功')
        return redirect(url_for('my_orders'))
    
    return render_template('place_order.html', book=book)

@app.route('/my-books')
def my_books():
    if 'user_id' not in session:
        flash('请先登录')
        return redirect(url_for('login'))
    
    books = load_data(BOOKS_FILE)
    my_books = [book for book in books if book['seller_id'] == session['user_id']]
    
    return render_template('my_books.html', books=my_books)

@app.route('/my-orders')
def my_orders():
    if 'user_id' not in session:
        flash('请先登录')
        return redirect(url_for('login'))
    
    orders = load_data(ORDERS_FILE)
    my_orders = [order for order in orders if order['buyer_id'] == session['user_id']]
    
    return render_template('my_orders.html', orders=my_orders)

@app.route('/my-sales')
def my_sales():
    if 'user_id' not in session:
        flash('请先登录')
        return redirect(url_for('login'))
    
    orders = load_data(ORDERS_FILE)
    my_sales = [order for order in orders if order['seller_id'] == session['user_id']]
    
    return render_template('my_sales.html', orders=my_sales)

if __name__ == '__main__':
    app.run(debug=True)