from flask import Blueprint, render_template, request, redirect
from database import db

interest_page = Blueprint('interest', __name__)

@interest_page.route('/<string:account_id>/interest/')
def interest(account_id):
    account = db.get_account(account_id)
    if not account:
        return redirect('/admin/account')
    return render_template('admin/account/interest.jinja', user=request.user, accountID=account[0])

@interest_page.route('/<string:account_id>/interest/', methods=['POST'])
def interest_post(account_id):
    account = db.get_account(account_id)
    amount = float(request.form.get('amount', 0))
    if not account:
        return redirect('/admin/account')
    db.change_interest(account_id, amount)
    return redirect(f'/admin/account/{account[0]}')