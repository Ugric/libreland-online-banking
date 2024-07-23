from flask import render_template, Blueprint, request, redirect
from database import db

pay_someone_page = Blueprint('pay_someone', __name__)

@pay_someone_page.route('/<path:account_id>/pay-someone')
def account(account_id):
    user = db.get_user_by_token(request.cookies.get('token'))
    if not user:
        return redirect('/login')
    account = db.get_account(account_id, user[0])
    if not account or account[1] == 1:
        return redirect('/dashboard')
    balance = db.get_balance(account_id)
    transactions = [
        {
            'id': transation[0],
            'amount': transation[2],
            'date': transation[3],
        }
        for transation in db.get_transactions(account_id)]
    recipients = []
    for user in filter(lambda recipient: recipient[0] != user[0], db.get_users()):
        recipients_account = db.get_users_first_current_account(user[0])
        if not recipients_account:
            continue
        recipients.append({
            'id': recipients_account[0],
            'name': user[1]
        })

    return render_template('dashboard/account/pay_someone/pay_someone.html', user=user, account={
        'id': account[0],
        'type': account[1],
        'name': account[2],
        'balance': balance
    }, transactions=reversed(transactions),recipients=recipients, error=request.args.get('error'))

@pay_someone_page.route('/<path:account_id>/pay-someone', methods=['POST'])
def account_post(account_id):
    user = db.get_user_by_token(request.cookies.get('token'))
    if not user:
        return redirect('/login')
    account = db.get_account(account_id, user[0])
    if not account or account[1] == 1:
        return redirect('/dashboard')
    recipient_id = request.form.get('recipient')
    reference = request.form.get('reference', '').strip()
    amount = int(float(request.form.get('amount'))*100)
    if amount == 0:
        return redirect('/dashboard/' + account_id + '/pay-someone?error=Please%20enter%20a%20valid%20amount')
    status = db.transfer(account_id, recipient_id, amount, reference)
    db.commit()
    match status:
        case 0:
            return redirect('/dashboard/' + account_id)
        case 1:
            return redirect('/dashboard/' + account_id + '/pay-someone?error=Invalid%20amount')
        case 2:
            return redirect('/dashboard/' + account_id + '/pay-someone?error=Insufficient%20funds')
        case 3:
            return redirect('/dashboard/' + account_id + '/pay-someone?error=Recipient%20account%20not%20found')
        case 4:
            return redirect('/dashboard/' + account_id + '/pay-someone?error=Same%20account')
        case _:
            return redirect('/dashboard/' + account_id + '/pay-someone?error=Internal%20error')