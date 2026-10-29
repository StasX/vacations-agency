"""Local HTTP development; select explicitly with DJANGO_SETTINGS_MODULE."""
from .base import *  # noqa: F401,F403

DEBUG = environ.get('DJANGO_DEBUG', 'true').strip().lower() in ('true', '1', 'yes', 'on')
AUTH_COOKIE_SECURE = environ.get('DJANGO_COOKIE_SECURE', 'false').strip().lower() in ('true', '1', 'yes', 'on')
SESSION_COOKIE_SECURE = AUTH_COOKIE_SECURE
CSRF_COOKIE_SECURE = AUTH_COOKIE_SECURE
