from flask import render_template, Blueprint, request, redirect, Response
from database import db

account_page = Blueprint('account', __name__)

@account_page.route('/<path:account_id>/')
def account(account_id):
    user = db.get_user_by_token(request.cookies.get('token'))
    if not user:
        return redirect('/login')
    account = db.get_account(account_id, user[0])
    if not account:
        return redirect('/dashboard')
    balance = db.get_balance(account_id)
    transactions = [
        {
            'id': transation[0],
            'amount': transation[2],
            'date': transation[3],
        }
        for transation in db.get_transactions(account_id)]
    return render_template('dashboard/account/account.html', user=user, account={
        'id': account[0],
        'name': account[2],
        'balance': balance
    }, transactions=reversed(transactions))
