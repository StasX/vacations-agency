from hmac import compare_digest
from secrets import token_urlsafe

from flask import request, session


def csrf_token():
    """Return an unpredictable token bound to the signed browser session."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = token_urlsafe(32)
    return session["_csrf_token"]


def init_csrf(app):
    app.config.setdefault("CSRF_ENABLED", True)
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_forms():
        if not app.config["CSRF_ENABLED"] or request.method in ("GET", "HEAD", "OPTIONS"):
            return
        expected = session.get("_csrf_token")
        submitted = request.form.get("csrf_token")
        if (not expected or not submitted or
                not compare_digest(expected.encode("utf-8"), submitted.encode("utf-8"))):
            return "Invalid or missing CSRF token. Reload the form and try again.", 400
