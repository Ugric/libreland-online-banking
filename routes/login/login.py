from flask import render_template, Blueprint, request, redirect
from database import db

login_page = Blueprint('login', __name__, url_prefix='/login')

@login_page.before_request
def check_login():
    if request.user:
        return redirect('/dashboard')

@login_page.route('/')
def login():
    return render_template('login/login.html')

@login_page.route('/', methods=['POST'])
def login_post():
    username = request.form.get("username")
    PIN = request.form.get("pin")
    login = db.login(username, PIN)
    if not login:
        return render_template('login/login.html', error='Invalid credentials')
    token = db.insert_token(login[0])
    db.commit()
    res = redirect('/dashboard')
    res.set_cookie('token', token, max_age=60*60*24*365)
    return res