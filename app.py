from flask import (
    Flask,
    session,
    redirect,
    url_for,
    request,
    render_template,
    current_app
)
from flask.ext.sqlalchemy import SQLAlchemy
import requests
import os
import json
import functools
import time

SQLALCHEMY_DATABASE_URI = os.environ.get(
    'HEROKU_POSTGRESQL_WHITE_URL',
    'sqlite:////tmp/test.db'
)
DEBUG = True
REDIRECT_URL = os.environ.get('REDIRECT_URL', 'http://localhost:5000/login')
CLEF_APP_ID = '4f318ac177a9391c2e0d221203725ffd'
CLEF_APP_SECRET = '2125d80f4583c52c46f8084bcc030c9b'
SECRET_KEY = 'development key'

app = Flask(__name__)
app.config.from_object(__name__)
db = SQLAlchemy(app)
db.create_all()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String())
    first_name = db.Column(db.String())
    clef_id = db.Column(db.Integer, unique=True)
    logged_out_at = db.Column(db.Integer)


def logged_in(view):
    """
    Decorator that checks whether a user is currently logged in.
    If a user is logged in it provides the user object.
    Uses Clef-based database logout.
    """
    @functools.wraps(view)
    def decorated_view(*args, **kwargs):
        user_id = session.get('user', -1)
        logged_in_at = session.get('logged_in_at', None)
        user = User.query.get(user_id)

        # does check for database logout of user
        if user and user.logged_out_at > logged_in_at:
            session.clear()
            user = None

        return view(user=user, *args, **kwargs)
    return decorated_view


@app.route('/')
@logged_in
def hello(user=None):
    return render_template(
        'index.html',
        user=user,
        redirect_url=current_app.config['REDIRECT_URL']
    )


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
        user = User(
            email=user_info['email'],
            first_name=user_info['first_name'],
            clef_id=user_info['id']
        )
        db.session.add(user)
        db.session.commit()

    session['user'] = user.id
    session['logged_in_at'] = time.time()

    return redirect(url_for('hello'))


class LogoutHookException(Exception):
    pass


@app.route('/logout')
@logged_in
def logout(user=None):
    if request.form.get("logout_token", None) is not None:
        data = dict(
            logout_token=request.form.get("logout_token"),
            app_id=CLEF_APP_ID,
            app_secret=CLEF_APP_SECRET
        )

        response = requests.post("https://clef.io/api/v1/logout", data=data)

        if response.status_code == 200:
            json_response = json.loads(response.text)

            if json_response.get('success', False):
                clef_id = json_response.get('clef_id', None)

                user = User.query.filter_by(clef_id=clef_id).first()

                user.logged_out_at = time.time()

                db.session.add(user)
                db.session.commit()

                return "ok"

    elif user:
        session.clear()
        return redirect(url_for('hello'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
