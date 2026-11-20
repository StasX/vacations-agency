from hmac import compare_digest
from secrets import token_urlsafe

from flask import abort, current_app, g, request
from itsdangerous import BadData, URLSafeTimedSerializer
from utils.auth_token import cookie_options, get_claims


COOKIE = "vacations_catalog_csrf"
LIFETIME = 60 * 60


def serializer():
    return URLSafeTimedSerializer(current_app.config["JWT_SECRET_KEY"], salt="catalog-anonymous-csrf")


def expected_token():
    claims = get_claims()
    if claims is not None:
        return claims["csrf"]
    signed = request.cookies.get(COOKIE)
    if signed:
        try:
            return serializer().loads(signed, max_age=LIFETIME)
        except BadData:
            pass
    return None


def csrf_token():
    token = expected_token()
    if token is None:
        if "new_csrf_token" not in g:
            g.new_csrf_token = token_urlsafe(32)
        return g.new_csrf_token
    return token


def clear_csrf_cookie(response):
    g.pop("new_csrf_token", None)
    response.delete_cookie(COOKIE, **cookie_options())
    return response


def init_csrf(app):
    app.config.setdefault("CSRF_ENABLED", True)
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.after_request
    def set_csrf_cookie(response):
        token = g.get("new_csrf_token")
        if token is not None:
            response.set_cookie(COOKIE, serializer().dumps(token), max_age=LIFETIME, **cookie_options())
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.before_request
    def protect_forms():
        if not app.config["CSRF_ENABLED"] or request.method in ("GET", "HEAD", "OPTIONS"):
            return
        expected = expected_token()
        submitted = request.form.get("csrf_token")
        if (not expected or not submitted or
                not compare_digest(expected.encode("utf-8"), submitted.encode("utf-8"))):
            abort(400, description="Invalid or missing CSRF token. Reload the form and try again.")
