from dotenv import load_dotenv
from os import environ

load_dotenv()


class AppConfig:
    mysql_host = environ.get("MYSQL_HOST")
    mysql_user = environ.get("MYSQL_USER")
    mysql_password = environ.get("MYSQL_PASSWORD")
    mysql_database = environ.get("MYSQL_DATABASE")
    session_secret_key = environ.get("SESSION_SECRET_KEY")
    session_cookie_secure = environ.get("FLASK_COOKIE_SECURE", "true").strip().lower() in ("true", "1", "yes", "on")
    passwords_salt = environ.get("PASSWORDS_SALT")
    redis_url = environ.get("JWT_REDIS_URL", "redis://localhost:6379/0")
    redis_password = environ.get("JWT_REDIS_PASSWORD")
