from flask import Flask, request, redirect
from database import db
from routes.home import home_page
from routes.login.login import login_page
from routes.dashboard.dashboard import dashboard_page
from waitress import serve
import os
import logging
import threading
import time
import datetime

def interesting_thread():
    time_now = datetime.datetime.now()
    secondsUntilMidnight = datetime.timedelta(
        hours=24 - time_now.hour,
        minutes=60 - time_now.minute,
        seconds=60 - time_now.second
    ).total_seconds()+1
    time.sleep(secondsUntilMidnight)
    while True:
        db.accumulate_interest()
        db.commit()
        time_now = datetime.datetime.now()
        secondsUntilMidnight = datetime.timedelta(
            hours=24 - time_now.hour,
            minutes=60 - time_now.minute,
            seconds=60 - time_now.second
        ).total_seconds()+1
        time.sleep(secondsUntilMidnight)
    
threading.Thread(target=interesting_thread).start()

logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)

def cents_to_libros(cents):
    libros = cents / 100
    return "{0:,.2f}₾".format(libros)

app = Flask(__name__, static_folder='static', static_url_path='')

app.jinja_env.filters['cents_to_libros'] = cents_to_libros

app.register_blueprint(home_page)

app.register_blueprint(login_page)

app.register_blueprint(dashboard_page)

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