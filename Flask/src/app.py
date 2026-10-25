from flask import Flask, render_template
from views.auth_view import auth_blueprint
from views.vacations_view import vacations_blueprint
from views.likes_view import likes_blueprint
from utils.app_config import AppConfig
from utils.logger import Logger
from utils.csrf import init_csrf

app = Flask(__name__)

# Create session secret key:
app.secret_key = AppConfig.session_secret_key
init_csrf(app)

app.register_blueprint(auth_blueprint)
app.register_blueprint(vacations_blueprint)
app.register_blueprint(likes_blueprint)


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html")


@app.errorhandler(405)
def method_not_allowed(error):
    return error


@app.errorhandler(Exception)
def catch_all(error):
    Logger.write_log(error)
    return render_template("500.html")
