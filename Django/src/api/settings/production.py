"""Production settings; HTTP/debug switches cannot weaken cookie security."""
from .base import *  # noqa: F401,F403

DEBUG = False
SESSION_COOKIE_SECURE = True
AUTH_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
