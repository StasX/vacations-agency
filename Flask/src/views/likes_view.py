
from flask import Blueprint, render_template, request, redirect, url_for
from facades.likes_facade import LikesFacade


likes_blueprint = Blueprint("likes_view", __name__)


@likes_blueprint.route("/likes/like/<int:id>", methods=["POST"])
def like(id):
    facade = LikesFacade()
    facade.like(id)
    return redirect(url_for("vacations_view.list"))
