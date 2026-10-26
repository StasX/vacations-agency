import jwt
from uuid import uuid4
from datetime import timedelta
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .app_config import AppConfig


def decode_token(token):
    """Verify server-selected signing settings and mandatory session claims."""
    claims = jwt.decode(
        token, AppConfig.secret_key, algorithms=["HS256"],
        audience=AppConfig.audience, issuer=AppConfig.issuer,
        options={"require": ["exp", "iat", "iss", "aud", "jti", "type", "user"]},
    )
    if not isinstance(claims.get('jti'), str) or not claims['jti']:
        raise jwt.InvalidTokenError('Invalid token identifier')
    return claims


def password_fingerprint(user):
    return salted_hmac('jwt-refresh-password', user.password, algorithm='sha256').hexdigest()


def issue_tokens(user, expires_at=None):
    now = timezone.now()
    expires_at = expires_at or now + timedelta(hours=1)
    payload = {
        'type': 'access',
        'user': {'id': user.pk, 'firstName': user.first_name,
                 'lastName': user.last_name, 'email': user.email,
                 'role': user.role.role_type},
        'exp': min(now + timedelta(minutes=10), expires_at),
        'iat': now, 'iss': AppConfig.issuer, 'aud': AppConfig.audience,
        'jti': str(uuid4()),
        'pwd': password_fingerprint(user),
    }
    access = jwt.encode(payload, AppConfig.secret_key, algorithm='HS256')
    payload.update(type='refresh', jti=str(uuid4()), exp=expires_at,
                   pwd=password_fingerprint(user))
    refresh = jwt.encode(payload, AppConfig.secret_key, algorithm='HS256')
    return access, refresh, expires_at
