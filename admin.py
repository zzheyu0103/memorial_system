from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Memorial
import pandas as pd, os
from werkzeug.utils import secure_filename

admin = Blueprint('admin', __name__)

@admin.route('/import', methods=['POST'])
@login_required
def import_excel():
    if current_user.role != 'admin':
        return jsonify({'error': '沒有權限'}), 403

    file = request.files['file']
    if file:
        os.makedirs('uploads', exist_ok=True)
        filepath = os.path.join('uploads', secure_filename(file.filename))
        file.save(filepath)
        df = pd.read_excel(filepath)
        for _, row in df.iterrows():
            m = Memorial(name=row['姓名'], side=row['側'], area=row['區'], row=row['行'], column=row['列'])
            db.session.add(m)
        db.session.commit()
        return jsonify({'status': 'success', 'message': '匯入完成'})
    return jsonify({'error': '未選擇檔案'})

@admin.route('/export')
@login_required
def export_excel():
    if current_user.role != 'admin':
        return jsonify({'error': '沒有權限'}), 403

    df = pd.read_sql(Memorial.query.statement, db.session.bind)
    filepath = 'memorials.xlsx'
    df.to_excel(filepath, index=False)
    return send_file(filepath, as_attachment=True)

@admin.route('/admin/memorials')
@login_required
def get_memorials():
    if current_user.role != 'admin':
        return jsonify({'error': '沒有權限'}), 403
    data = Memorial.query.all()
    return jsonify([{
        'id': m.id, 'name': m.name, 'side': m.side,
        'area': m.area, 'row': m.row, 'column': m.column
    } for m in data])

@admin.route('/delete/<int:id>', methods=['DELETE'])
@login_required
def delete_memorial(id):
    if current_user.role != 'admin':
        return jsonify({'error': '沒有權限'}), 403
    Memorial.query.filter_by(id=id).delete()
    db.session.commit()
    return jsonify({'status': 'success'})
