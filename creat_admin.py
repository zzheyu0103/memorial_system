from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin():
    username = input("輸入管理者帳號: ")
    password = input("輸入密碼: ")
    hashed_password = generate_password_hash(password)
    
    with app.app_context():
        if not User.query.filter_by(username=username).first():
            admin = User(username=username, password_hash=hashed_password, role='admin')
            db.session.add(admin)
            db.session.commit()
            print("管理者帳號建立完成！")
        else:
            print("此帳號已存在")

if __name__ == '__main__':
    create_admin()
