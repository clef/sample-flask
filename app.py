from flask import (
    Flask,
    session,
    redirect,
    url_for,
    request,
    render_template)
from flask.ext.sqlalchemy import SQLAlchemy
import requests
import os
import json

SQLALCHEMY_DATABASE_URI = 'sqlite:////tmp/test.db'
DEBUG = True
CLEF_APP_ID = '4f318ac177a9391c2e0d221203725ffd'
CLEF_APP_SECRET = '2125d80f4583c52c46f8084bcc030c9b'
SECRET_KEY = 'development key'

app = Flask(__name__)
app.config.from_object(__name__)
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String())
    first_name = db.Column(db.String())
    clef_id = db.Column(db.Integer, unique=True)

@app.route('/')
def hello():
    user_id = session.get('user')
    user = User.query.filter_by(id=user_id).first()
    return render_template('index.html', user=user)

@app.route('/logout')
def logout():
    session.pop('user')
    return redirect(url_for('hello'))

@app.route('/login')
def login():
    code = request.args.get('code')
    data = {
        'app_id': app.config['CLEF_APP_ID'],
        'app_secret': app.config['CLEF_APP_SECRET'],
        'code': code
    }
    response = requests.post('https://clef.io/api/v1/authorize', data=data)
    json_response = json.loads(response.text)

    if json_response.get('error'):
        return json_response['error']

    token = json_response['access_token']
    response = requests.get('https://clef.io/api/v1/info?access_token=%s' % token)
    json_response = json.loads(response.text)

    if json_response.get('error'):
        return json_response['error']

    user_info = json_response['info']
    user = User.query.filter_by(clef_id=user_info['id']).first()
    if not user:
        user = User(email=user_info['email'],
            first_name=user_info['first_name'],
            clef_id=user_info['id'])
        db.session.add(user)
        db.session.commit()

    session['user'] = user.id
    return redirect(url_for('hello'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
