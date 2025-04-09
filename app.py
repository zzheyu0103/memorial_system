from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
import pandas as pd
from datetime import datetime
import difflib
import json
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///memorial.db'
db = SQLAlchemy(app)

# 登入管理
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 紀念名牌模型
class Memorial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    side = db.Column(db.String(10), nullable=False)
    area = db.Column(db.Integer, nullable=False)
    row = db.Column(db.Integer, nullable=False)
    column = db.Column(db.Integer, nullable=False)

# 使用者模型
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), default='general')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 活動紀錄
class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    action = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_request
def restrict_admin_routes():
    admin_routes = ['/import', '/export', '/add', '/delete', '/edit', '/backup', '/restore', '/logs']
    if any(request.path.startswith(route) for route in admin_routes):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'error': '無權限'}), 403

# 登入
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        user = User.query.filter_by(username=data['username']).first()
        if user and user.check_password(data['password']):
            login_user(user)
            return redirect(url_for('index'))
        return render_template('login.html', error='帳號或密碼錯誤')
    return render_template('login.html')

# 登出
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# 查詢主畫面
@app.route('/')
def index():
    return render_template('index.html')

# 查詢紀念名牌（模糊搜尋）
@app.route('/search')
def search():
    name = request.args.get('name')
    results = Memorial.query.all()
    close_matches = difflib.get_close_matches(name, [m.name for m in results], n=10, cutoff=0.5)

    output = []
    for match in close_matches:
        m = Memorial.query.filter_by(name=match).first()
        sentence = f"{m.name} 的紀念名牌在{'左側' if m.side == 'left' else '右側'}第 {m.area} 區的 {m.row} 行 {m.column} 列。"
        english = f"{m.name}'s memorial plaque is in Area {m.area}, Row {m.row}, Column {m.column} on the {'left' if m.side == 'left' else 'right'} side."
        output.append({'name': m.name, 'result': sentence, 'english': english})
    return jsonify(output)

# 自動完成名稱
@app.route('/autocomplete')
def autocomplete():
    names = [m.name for m in Memorial.query.all()]
    return jsonify(names)

# 匯入 Excel
@app.route('/import', methods=['POST'])
def import_excel():
    file = request.files['file']
    df = pd.read_excel(file)
    added = 0
    for _, row in df.iterrows():
        if not Memorial.query.filter_by(name=row['name']).first():
            memorial = Memorial(name=row['name'], side=row['side'], area=row['area'], row=row['row'], column=row['column'])
            db.session.add(memorial)
            added += 1
    db.session.commit()
    log_action(f"匯入 {added} 筆資料")
    return jsonify({'status': 'success', 'added': added})

# 匯出 Excel
@app.route('/export')
def export_excel():
    data = Memorial.query.all()
    df = pd.DataFrame([{
        'name': m.name,
        'side': m.side,
        'area': m.area,
        'row': m.row,
        'column': m.column
    } for m in data])
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    log_action("匯出資料")
    return send_file(output, as_attachment=True, download_name='memorial_export.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# 新增資料
@app.route('/add', methods=['POST'])
def add():
    data = request.json
    if not Memorial.query.filter_by(name=data['name']).first():
        memorial = Memorial(**data)
        db.session.add(memorial)
        db.session.commit()
        log_action(f"新增：{data['name']}")
        return jsonify({'status': 'success'})
    return jsonify({'status': 'duplicate'})

# 編輯資料
@app.route('/edit/<int:id>', methods=['POST'])
def edit(id):
    memorial = Memorial.query.get(id)
    data = request.json
    if memorial:
        memorial.name = data['name']
        memorial.side = data['side']
        memorial.area = data['area']
        memorial.row = data['row']
        memorial.column = data['column']
        db.session.commit()
        log_action(f"編輯：{data['name']}")
        return jsonify({'status': 'success'})
    return jsonify({'status': 'not found'})

# 刪除資料
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    memorial = Memorial.query.get(id)
    if memorial:
        log_action(f"刪除：{memorial.name}")
        db.session.delete(memorial)
        db.session.commit()
        return jsonify({'status': 'success'})
    return jsonify({'status': 'not found'})

# 區域統計
@app.route('/stats')
def stats():
    stats = db.session.query(Memorial.side, Memorial.area, db.func.count()).group_by(Memorial.side, Memorial.area).all()
    result = [{'side': s, 'area': a, 'count': c} for s, a, c in stats]
    return jsonify(result)

# 活動紀錄
@app.route('/logs')
def logs():
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()
    return jsonify([{
        'user': log.username,
        'action': log.action,
        'time': log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for log in logs])

# 備份
@app.route('/backup')
def backup():
    data = Memorial.query.all()
    export = [{
        'name': m.name,
        'side': m.side,
        'area': m.area,
        'row': m.row,
        'column': m.column
    } for m in data]
    log_action("備份資料")
    return jsonify(export)

# 還原
@app.route('/restore', methods=['POST'])
def restore():
    data = request.json
    Memorial.query.delete()
    for item in data:
        db.session.add(Memorial(**item))
    db.session.commit()
    log_action("還原資料")
    return jsonify({'status': 'success'})

# 活動紀錄寫入函式
def log_action(action):
    if current_user.is_authenticated:
        log = ActivityLog(username=current_user.username, action=action)
        db.session.add(log)
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
