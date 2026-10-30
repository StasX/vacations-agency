"""Isolated settings: never load repository .env credentials or connect to MySQL."""
from unittest.mock import patch

with patch('dotenv.load_dotenv'):
    from utils.app_config import AppConfig

# Also supports signing HS512 tokens used to test rejected algorithms.
AppConfig.secret_key = 'django-tests-only-secret-key-at-least-64-bytes-for-hs512-validation'
AppConfig.passwords_salt = 'test-only-salt'
AppConfig.issuer = 'test-issuer'
AppConfig.audience = 'test-audience'

from api.settings import *  # noqa: E402,F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
SECRET_KEY = AppConfig.secret_key
DEBUG = False
ALLOWED_HOSTS = ['testserver', 'localhost']
MIGRATION_MODULES = {'users': None, 'vacations': None, 'likes': None}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
# Keep intentional HTTP 500 tests from triggering Django's email/template reporter.
# Django 5.0's template context copying is incompatible with Python 3.14.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'null': {'class': 'logging.NullHandler'}},
    'loggers': {'django.request': {'handlers': ['null'], 'propagate': False}},
}
