from flask import render_template, request, Blueprint, redirect
from database import db

admin_page = Blueprint('admin', __name__, url_prefix='/admin')

@admin_page.before_request
def check_admin():
    if not request.user:
        return redirect('/login')
    if not request.user[4]:
        return redirect('/dashboard')

@admin_page.route('/')
def admin():
    return render_template('admin/admin.html', user=request.user)