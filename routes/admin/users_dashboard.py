from flask import Blueprint, render_template, request, redirect
from database import db

users_dashboard_page = Blueprint('user', __name__, url_prefix='/user')

@users_dashboard_page.route('/')
def users():
    users = db.get_users(show_hidden=True)
    users_output = []
    for user in users:
        users_output.append({'name': user[1], 'id': user[0]})
    return render_template('admin/user.html', user=request.user, users=users_output)

@users_dashboard_page.route('/', methods=['POST'])
def search_users():
    userID = request.form.get('userID')
    user = db.get_user_by_id(userID)
    if not user:
        users = db.get_users(show_hidden=True)
        users_output = []
        for user in users:
            users_output.append({'name': user[1], 'id': user[0]})
        return render_template('admin/user.html', user=request.user, users=users, error='User was not found')
    db.commit()
    return redirect(f'/admin/user/{userID}')

@users_dashboard_page.route('/<string:userID>/')
def users_dashboard(userID):
    user = db.get_user_by_id(userID)
    if not user:
        return redirect("/admin")
    accounts = db.get_accounts(user[0])
    accounts_with_balance = []
    for account in accounts:
        balance = db.get_balance(account[0])
        accounts_with_balance.append({
            'id': account[0],
            'name': account[2],
            'balance': balance
        })
    return render_template('admin/user-dashboard.html', user=request.user, opened_user=user, accounts=accounts_with_balance)