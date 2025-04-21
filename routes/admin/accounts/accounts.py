from flask import Blueprint, render_template, request, redirect
from database import db
from routes.admin.accounts.exchange import exchange_page
from routes.admin.accounts.interest import interest_page

accounts_page = Blueprint('accounts', __name__, url_prefix='/account')

@accounts_page.route('/')
def accounts():
    return render_template('admin/account/accounts.html', user=request.user)

@accounts_page.route('/', methods=['POST'])
def search_account():
    account_ID = request.form.get('account_ID')
    account = db.get_account(account_ID)
    if not account:
        return render_template('admin/account/accounts.html', user=request.user, error='Account not found')
    return redirect(f'/admin/account/{account_ID}')

@accounts_page.route('/<string:account_id>/')
def account(account_id):
    account = db.get_account(account_id)
    if not account:
        return redirect('/admin/account')
    balance = db.get_balance(account_id)
    transactions = [
        {
            'id': transation[0],
            'amount': transation[2],
            'date': transation[3],
        }
        for transation in db.get_transactions(account_id)]
    interest_rate = account[5]
    interest_accumulated = int(db.get_interest_accumulated(account_id))
    interest_Since_last = db.calculate_interest(account_id)
    return render_template('admin/account/account.html', user=request.user, account={
        'id': account[0],
        'type': account[1],
        'name': account[2],
        'balance': balance
    },
    transactions=reversed(transactions),
    interest={
        'rate': interest_rate,
        'accumulated': interest_accumulated,
        'since_last': interest_Since_last
    })

accounts_page.register_blueprint(exchange_page)
accounts_page.register_blueprint(interest_page)