from flask import Flask, request, redirect
from database import db
from routes.home import home_page
from routes.login.login import login_page
from routes.dashboard.dashboard import dashboard_page

app = Flask(__name__, static_folder='static', static_url_path='')

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


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)