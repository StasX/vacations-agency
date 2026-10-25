
from flask import Blueprint, render_template, request, redirect, url_for
from facades.likes_facade import LikesFacade
from facades.auth_facade import AuthFacade
from models.client_errors import AuthError


likes_blueprint = Blueprint("likes_view", __name__)


@likes_blueprint.route("/likes/like/<int:id>", methods=["POST"])
def like(id):
    try:
        AuthFacade().block_anonymous()
        facade = LikesFacade()
        facade.like(id)
        return redirect(url_for("vacations_view.list"))
    except AuthError:
        return redirect(url_for("auth_view.login"))
