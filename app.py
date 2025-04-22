from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.utils import secure_filename
import os
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 模擬資料庫
memorials = []
users = {
    'admin': {'password': '1234', 'role': 'admin'},
    'user': {'password': '1234', 'role': 'user'}
}

class User(UserMixin):
    def __init__(self, id, role):
        self.id = id
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id, users[user_id]['role'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    name = request.args.get('name')
    results = [m for m in memorials if m['name'] == name]
    return jsonify(results=[{'result': f"{m['side']}側，第{m['area']}區 {m['row']}行{m['column']}列"} for m in results])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users.get(username)
        if user and user['password'] == password:
            login_user(User(username, user['role']))
            return redirect(url_for('index'))
        return '登入失敗'
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/import', methods=['POST'])
@login_required
def import_excel():
    if current_user.role != 'admin':
        return jsonify({'error': '沒有權限'}), 403

    file = request.files['file']
    if file:
        if not os.path.exists('uploads'):
            os.makedirs('uploads')

        filename = secure_filename(file.filename)
        filepath = os.path.join('uploads', filename)
        file.save(filepath)

        df = pd.read_excel(filepath)
        for _, row in df.iterrows():
            memorials.append({
                'id': len(memorials) + 1,
                'name': row['姓名'],
                'side': row['側'],
                'area': row['區'],
                'row': row['行'],
                'column': row['列']
            })
        return jsonify({'status': 'success', 'message': '匯入完成'})
    return jsonify({'error': '未選擇檔案'})

@app.route('/export')
@login_required
def export_excel():
    if current_user.role != 'admin':
        return jsonify({'error': '沒有權限'}), 403

    df = pd.DataFrame(memorials)
    filepath = 'memorials.xlsx'
    df.to_excel(filepath, index=False)
    return send_file(filepath, as_attachment=True)

@app.route('/admin/memorials')
@login_required
def get_memorials():
    if current_user.role != 'admin':
        return jsonify({'error': '沒有權限'}), 403
    return jsonify(memorials)

@app.route('/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_memorial(id):
    if current_user.role != 'admin':
        return jsonify({'error': '沒有權限'}), 403
    global memorials
    memorials = [m for m in memorials if m['id'] != id]
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    memorials.clear()

    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    app.run(debug=True)

