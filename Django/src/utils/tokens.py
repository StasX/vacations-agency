import jwt

from .app_config import AppConfig


def decode_token(token):
    """Verify server-selected signing settings and mandatory session claims."""
    return jwt.decode(
        token, AppConfig.secret_key, algorithms=["HS256"],
        audience=AppConfig.audience, issuer=AppConfig.issuer,
        options={"require": ["exp", "iat", "iss", "aud", "jti", "type", "user"]},
    )
