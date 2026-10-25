from flask import Blueprint, render_template, request, redirect, url_for, session
from facades.auth_facade import AuthFacade
from models.client_errors import ValidationError, AuthError

auth_blueprint = Blueprint("auth_view", __name__)


@auth_blueprint.route("/", methods=["GET", "POST"])
@auth_blueprint.route("/login", methods=["GET", "POST"])
def login():
    try:
        if request.method == "GET":
            return render_template("login.html", user={})
        auth_facade = AuthFacade()
        auth_facade.login()

        return redirect(url_for("vacations_view.list"))
    except (ValidationError, AuthError) as error:
        return render_template("login.html", error="Invalid Email or Password.", user=error.model)


@auth_blueprint.route("/register", methods=["GET", "POST"])
def register():
    try:
        if request.method == "GET":
            return render_template("register.html", user={})
        auth_facade = AuthFacade()
        auth_facade.register()
        return redirect(url_for("vacations_view.list"))
    except ValidationError as err:
        return render_template("register.html", error=err.message, user=err.model)


@auth_blueprint.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth_view.login"))
