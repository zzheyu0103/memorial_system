from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask import render_template
from marshmallow import Schema, fields

import pandas as pd
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# 使用 SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///memorials.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 紀念牌資料表
class Memorial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

# 建立資料庫
with app.app_context():
    db.create_all()
    
# Flask 加上首頁 
@app.route('/')
def index():
    return render_template('index.html')

# 上傳檔案
UPLOAD_FOLDER = 'instance/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/admin/import', methods=['POST'])
def import_excel():
    if 'file' not in request.files:
        return jsonify({"error": "未找到檔案"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "未選擇檔案"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        df = pd.read_excel(filepath)
        for _, row in df.iterrows():
            if pd.isnull(row.get('name')) or pd.isnull(row.get('location')):
                continue
            memorial = Memorial(
                name=row.get('name'),
                location=row.get('location'),
                description=row.get('description', ''),
                latitude=row.get('latitude'),
                longitude=row.get('longitude')
            )
            db.session.add(memorial)
        db.session.commit()
        return jsonify({"message": "匯入成功"}), 201
    except Exception as e:
        return jsonify({"error": f"處理錯誤：{str(e)}"}), 500



# 查看所有紀念牌資料
@app.route('/admin/memorials', methods=['GET'])
def get_all_memorials():
    memorials = Memorial.query.all()
    return jsonify([{
        "id": m.id,
        "name": m.name,
        "location": m.location,
        "description": m.description,
        "latitude": m.latitude,
        "longitude": m.longitude
    } for m in memorials])


# 編輯紀念牌資料 API
@app.route('/admin/edit/<int:id>', methods=['PUT'])
def edit_memorial(id):
    memorial = Memorial.query.get_or_404(id)
    
    data = request.json
    memorial.name = data.get('name', memorial.name)
    memorial.location = data.get('location', memorial.location)
    memorial.description = data.get('description', memorial.description)
    memorial.latitude = data.get('latitude', memorial.latitude)
    memorial.longitude = data.get('longitude', memorial.longitude)
    
    db.session.commit()
    return jsonify({"message": "更新成功"})

# 刪除紀念牌資料 API
@app.route('/admin/delete/<int:id>', methods=['DELETE'])
def delete_memorial(id):
    memorial = Memorial.query.get_or_404(id)
    db.session.delete(memorial)
    db.session.commit()
    return jsonify({"message": "刪除成功"})


# 增加資料驗證
class MemorialSchema(Schema):
    name = fields.Str(required=True)
    location = fields.Str(required=True)
    description = fields.Str()
    latitude = fields.Float()
    longitude = fields.Float()

# 在新增或更新資料前進行驗證
@app.route('/admin/add', methods=['POST'])
def add_memorial():
    data = request.json
    schema = MemorialSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify(errors), 400
    
    new_memorial = Memorial(**data)
    db.session.add(new_memorial)
    db.session.commit()
    return jsonify({"message": "新增成功"}), 201

# 錯誤處理
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "找不到資料"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "伺服器錯誤"}), 500

# 模糊搜尋、根據位置範圍查詢
@app.route('/search', methods=['GET'])
def search():
    name_query = request.args.get('name', '').strip()
    location_query = request.args.get('location', '').strip()
    
    query = Memorial.query
    if name_query:
        query = query.filter(Memorial.name.like(f"%{name_query}%"))
    if location_query:
        query = query.filter(Memorial.location.like(f"%{location_query}%"))
    
    results = query.all()
    return jsonify([{"id": m.id, "name": m.name, "location": m.location} for m in results])



# 啟動伺服器
if __name__ == '__main__':
    app.run(debug=True)
