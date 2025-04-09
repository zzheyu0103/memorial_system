from app import app, db

with app.app_context():
    db.create_all()
    print("資料庫初始化完成！")
