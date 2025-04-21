from flask import Blueprint, render_template, request, redirect
from database import db

create_account_page = Blueprint('create-account', __name__, url_prefix='/create-account')

@create_account_page.route('/')
def accounts():
    users = db.get_users(show_hidden=True)
    users_output = []
    for user in users:
        users_output.append({'name': user[1], 'id': user[0]})
    return render_template('admin/create-account.html', user=request.user, users=users_output)

@create_account_page.route('/', methods=['POST'])
def search_account():
    userID = request.form.get('userID')
    accountType = int(request.form.get('type', 0))
    print(accountType)
    accountName = request.form.get('name', 'Current Account')
    accountInterest = float(request.form.get('interest', 0))
    accountID = db.insert_account(userID, accountType, accountName, accountInterest)
    if not accountID:
        users = db.get_users(show_hidden=True)
        users_output = []
        for user in users:
            users_output.append({'name': user[1], 'id': user[0]})
        return render_template('admin/create-account.html', user=request.user, error='Account could not be created', users=users_output)
    db.insert_transaction(accountID, 0, 'Initial Balance')
    db.commit()
    return redirect(f'/admin/account/{accountID}')