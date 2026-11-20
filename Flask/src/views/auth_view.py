from flask import Blueprint, render_template, request, redirect, url_for
from facades.auth_facade import AuthFacade
from models.client_errors import ValidationError, AuthError
from utils import login_limiter
from utils.auth_token import revoke_token, set_auth_cookie
from utils.csrf import clear_csrf_cookie

auth_blueprint = Blueprint("auth_view", __name__)


@auth_blueprint.route("/", methods=["GET", "POST"])
@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    try:
        if request.method == "GET":
            return render_template("login.html", user={})
        retry = login_limiter.retry_after(request.remote_addr, request.form.get('email'))
        if retry:
            return render_template("login.html", user={}, error="Too many login attempts. Please try again later."), 429, {'Retry-After': str(retry), 'Cache-Control': 'no-store'}
        auth_facade = AuthFacade()
        token = auth_facade.login()
        return clear_csrf_cookie(set_auth_cookie(redirect(url_for("vacations_view.list")), token))
    except (ValidationError, AuthError) as error:
        return render_template("login.html", error="Invalid Email or Password.", user=error.model)


@auth_blueprint.route("/register", methods=["GET", "POST"])
def register():
    try:
        if request.method == "GET":
            return render_template("register.html", user={})
        auth_facade = AuthFacade()
        token = auth_facade.register()
        return clear_csrf_cookie(set_auth_cookie(redirect(url_for("vacations_view.list")), token))
    except ValidationError as err:
        return render_template("register.html", error=err.message, user=err.model)


@auth_blueprint.route("/logout", methods=["POST"])
def logout():
    revoke_token()
    return clear_csrf_cookie(redirect(url_for("auth_view.login")))
