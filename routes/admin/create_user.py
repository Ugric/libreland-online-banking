from flask import Blueprint, render_template, request, redirect
from database import db

create_user_page = Blueprint('create-user', __name__, url_prefix='/create-user')

@create_user_page.route('/')
def accounts():
    return render_template('admin/create-user.html', user=request.user)

@create_user_page.route('/', methods=['POST'])
def search_account():
    username = request.form.get('username')
    hidden = bool(request.form.get('hidden'))
    admin = bool(request.form.get('admin'))
    userID = db.insert_user(username, hidden=hidden, admin=admin)
    if not userID:
        return render_template('admin/create-user.html', user=request.user, error='User could not be created')
    db.commit()
    return redirect(f'/admin/user/{userID}')