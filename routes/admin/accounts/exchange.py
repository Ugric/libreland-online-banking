from flask import Blueprint, render_template, request, redirect
from database import db

exchange_page = Blueprint('exchange', __name__)

@exchange_page.route('/<string:account_id>/exchange/')
def exchange(account_id):
    account = db.get_account(account_id)
    if not account:
        return redirect('/admin/account')
    return render_template('admin/account/exchange.html', user=request.user, accountID=account[0])

@exchange_page.route('/<string:account_id>/exchange/', methods=['POST'])
def exchange_post(account_id):
    account = db.get_account(account_id)
    amount = int(request.form.get('amount', 0))
    reference = request.form.get('reference')
    if not account:
        return redirect('/admin/account')
    db.insert_transaction(account[0], amount, reference)
    return redirect(f'/admin/account/{account[0]}')