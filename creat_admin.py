from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    username = input("輸入帳號: ")
    password = input("輸入密碼: ")
    if User.query.filter_by(username=username).first():
        print("帳號已存在")
    else:
        user = User(username=username, password=generate_password_hash(password), role='admin')
        db.session.add(user)
        db.session.commit()
        print("管理員建立完成")
