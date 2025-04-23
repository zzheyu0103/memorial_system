from flask import Flask, render_template, request, jsonify
from flask_login import LoginManager, current_user
from models import db, User, Memorial
from auth import auth
from admin import admin

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/memorial.db'
app.config['SECRET_KEY'] = 'your_secret_key'

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

app.register_blueprint(auth)
app.register_blueprint(admin)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    name = request.args.get('name')
    results = Memorial.query.filter_by(name=name).all()
    return jsonify(results=[{
        'result': f"{m.side}側，第{m.area}區 {m.row}行{m.column}列"
    } for m in results])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
