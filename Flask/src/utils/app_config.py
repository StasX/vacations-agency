from dotenv import load_dotenv
from os import environ
from config import get_config

load_dotenv()


class AppConfig:
    flask_config = get_config()
    mysql_host = environ.get("MYSQL_HOST")
    mysql_user = environ.get("MYSQL_USER")
    mysql_password = environ.get("MYSQL_PASSWORD")
    mysql_database = environ.get("MYSQL_DATABASE")
    session_secret_key = environ.get("SESSION_SECRET_KEY")
    session_cookie_secure = flask_config.SESSION_COOKIE_SECURE
    passwords_salt = environ.get("PASSWORDS_SALT")
    redis_url = environ.get("JWT_REDIS_URL", "redis://localhost:6379/0")
    redis_password = environ.get("JWT_REDIS_PASSWORD")
