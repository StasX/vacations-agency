from flask import Flask, render_template
import logging
from werkzeug.exceptions import HTTPException, ServiceUnavailable
from views.auth_view import auth_blueprint
from views.vacations_view import vacations_blueprint
from views.likes_view import likes_blueprint
from utils.app_config import AppConfig
from utils.logger import Logger
from utils.csrf import init_csrf
from utils.dal import close_request_connections
from models.client_errors import ResourceNotFoundError
from redis.exceptions import RedisError

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(name)s: %(message)s')
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

# Create session secret key:
app.secret_key = AppConfig.session_secret_key
app.config.update(
    SESSION_COOKIE_SECURE=AppConfig.session_cookie_secure,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
init_csrf(app)
app.teardown_request(close_request_connections)

app.register_blueprint(auth_blueprint)
app.register_blueprint(vacations_blueprint)
app.register_blueprint(likes_blueprint)


@app.errorhandler(404)
@app.errorhandler(ResourceNotFoundError)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(405)
def method_not_allowed(error):
    response = error.get_response()
    response.set_data(render_template("405.html"))
    response.content_type = "text/html; charset=utf-8"
    return response


@app.errorhandler(HTTPException)
def http_error(error):
    # Start with the original response to retain headers such as Retry-After.
    response = error.get_response()
    response.set_data(render_template("http_error.html", error=error))
    response.content_type = "text/html; charset=utf-8"
    return response


@app.errorhandler(Exception)
def catch_all(error):
    Logger.write_log(error)
    return render_template("500.html"), 500


@app.errorhandler(RedisError)
def auth_unavailable(error):
    Logger.write_log(error)
    return render_template("http_error.html", error=ServiceUnavailable(description="Authentication temporarily unavailable")), 503, {'Retry-After': '5'}
