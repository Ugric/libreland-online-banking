from flask import render_template, Blueprint, request, redirect, Response
from database import db
from .account.account import account_page

dashboard_page = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_page.route('/')
def login():
    user = db.get_user_by_token(request.cookies.get('token'))
    if not user:
        return redirect('/login')
    accounts = db.get_accounts(user[0])
    accounts_with_balance = []
    for account in accounts:
        balance = db.get_balance(account[0])
        accounts_with_balance.append({
            'id': account[0],
            'name': account[2],
            'balance': balance
        })
    return render_template('dashboard/dashboard.html', user=user, accounts=accounts_with_balance)

dashboard_page.register_blueprint(account_page)