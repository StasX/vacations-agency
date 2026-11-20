"""Explicit Flask profiles. Production is the default outside development."""
from os import environ


class ProductionConfig:
    DEBUG = False
    AUTH_COOKIE_SECURE = True
    CSRF_ENABLED = True


class DevelopmentConfig(ProductionConfig):
    DEBUG = True
    AUTH_COOKIE_SECURE = False


def get_config():
    environment = environ.get('APP_ENV', 'production').strip().lower()
    if environment == 'production':
        return ProductionConfig
    if environment == 'development':
        class LocalConfig(DevelopmentConfig):
            AUTH_COOKIE_SECURE = environ.get('FLASK_COOKIE_SECURE', 'false').strip().lower() in ('true', '1', 'yes', 'on')
        return LocalConfig
    raise ValueError('APP_ENV must be development or production')
