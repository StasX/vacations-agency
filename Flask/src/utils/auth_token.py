from secrets import token_urlsafe
from time import time
from uuid import uuid4

import jwt
from flask import current_app, g, request

from utils import auth_status
from utils.security import Security


COOKIE = "vacations_catalog_jwt"
LIFETIME = 8 * 60 * 60
ISSUER = "vacations-catalog"
AUDIENCE = "vacations-catalog-browser"
CLAIMS = ["sub", "jti", "iat", "exp", "iss", "aud", "status", "role", "pwd", "csrf"]


def issue_token(user, status):
    now = int(time())
    return jwt.encode({
        "sub": str(user["id"]),
        "jti": uuid4().hex,
        "iat": now,
        "exp": now + LIFETIME,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "status": status,
        "role": user["role"],
        "pwd": Security.password_fingerprint(user["password"]),
        "csrf": token_urlsafe(32),
    }, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def get_claims():
    if "auth_claims" not in g:
        g.auth_claims = None
        token = request.cookies.get(COOKIE)
        if token is not None:
            try:
                claims = jwt.decode(
                    token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"],
                    issuer=ISSUER, audience=AUDIENCE, options={"require": CLAIMS},
                )
                subject = claims["sub"]
                if (not subject.isascii() or not subject.isdecimal()
                        or len(subject) > 20 or int(subject) <= 0
                        or not all(isinstance(claims[key], str) and claims[key].isascii()
                                   for key in ("csrf", "pwd"))):
                    raise jwt.InvalidTokenError("Invalid catalog claims")
                g.auth_claims = claims
            except jwt.InvalidTokenError:
                clear_claims()
    return g.auth_claims


def clear_claims():
    g.auth_claims = None
    g.clear_auth_cookie = True


def revocation_key(claims):
    return f'vacations:jwt:catalog-revoked:{claims["jti"]}'


def is_revoked(claims):
    return bool(auth_status.get_redis().exists(revocation_key(claims)))


def revoke_token():
    claims = get_claims()
    if claims is not None:
        auth_status.get_redis().set(revocation_key(claims), "1", exat=claims["exp"])
    clear_claims()


def cookie_options():
    return {"secure": current_app.config["AUTH_COOKIE_SECURE"],
            "httponly": True, "samesite": "Lax"}


def set_auth_cookie(response, token):
    response.set_cookie(COOKIE, token, max_age=LIFETIME, **cookie_options())
    response.headers["Cache-Control"] = "no-store"
    g.clear_auth_cookie = False
    return response


def init_auth_token(app):
    app.jinja_env.globals["auth_claims"] = get_claims

    @app.after_request
    def remove_invalid_cookie(response):
        if "auth_claims" in g:
            response.vary.add("Cookie")
        if g.get("auth_claims") is not None and not response.cache_control.no_store:
            response.cache_control.private = True
        if g.get("clear_auth_cookie"):
            response.delete_cookie(COOKIE, **cookie_options())
            response.headers["Cache-Control"] = "no-store"
        return response
