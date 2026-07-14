from flask import render_template, request, Blueprint, redirect
from routes.admin.accounts.accounts import accounts_page
from routes.admin.create_user import create_user_page
from routes.admin.users_dashboard import users_dashboard_page
from routes.admin.create_account import create_account_page

admin_page = Blueprint('admin', __name__, url_prefix='/admin')

@admin_page.before_request
def check_admin():
    if not request.user:
        return redirect('/login')
    if not request.user[4]:
        return redirect('/dashboard')

@admin_page.route('/')
def admin():
    return render_template('admin/admin.jinja', user=request.user)

admin_page.register_blueprint(accounts_page)
admin_page.register_blueprint(create_user_page)
admin_page.register_blueprint(users_dashboard_page)
admin_page.register_blueprint(create_account_page)