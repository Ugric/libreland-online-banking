from flask import Flask, request, redirect
from database import db
from routes.home import home_page
from routes.login.login import login_page
from routes.dashboard.dashboard import dashboard_page
from routes.admin.admin import admin_page
from waitress import serve
import os
import logging
import threading
import time
import datetime

def interesting_thread():
    while True:
        time_now = datetime.datetime.now()
        secondsUntilMidnight = datetime.timedelta(
            hours=23 - time_now.hour,
            minutes=59 - time_now.minute,
            seconds=60 - time_now.second
        ).total_seconds()+1
        print(secondsUntilMidnight)
        time.sleep(secondsUntilMidnight)
        db.accumulate_interest()
    
threading.Thread(target=interesting_thread).start()

logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

def cents_to_libros(cents):
    libros = cents / 100
    return "{0:,.2f}₾".format(libros)

def cents_to_libros_4dp(cents):
    libros = cents / 100
    return "{0:,.4f}₾".format(libros)

app = Flask(__name__, static_folder='static', static_url_path='')

app.jinja_env.filters['cents_to_libros'] = cents_to_libros
app.jinja_env.filters['cents_to_libros_4dp'] = cents_to_libros_4dp

@app.before_request
def before_request():
    request.user = db.get_user_by_token(request.cookies.get('token'))

app.register_blueprint(home_page)

app.register_blueprint(login_page)

app.register_blueprint(dashboard_page)

app.register_blueprint(admin_page)

@app.route('/logout')
def logout():
    token = request.cookies.get('token')
    db.delete_token(token)
    db.commit()
    res = redirect('/login')
    res.set_cookie('token', '', max_age=0)
    return res

if bool(os.environ.get("DEBUG")):
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5000)
else:
    serve(app, host="0.0.0.0", port=5000)