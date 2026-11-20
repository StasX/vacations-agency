
from flask import g
from logic.likes_logic import LikesLogic
from facades.auth_facade import AuthFacade


class LikesFacade:
    def __init__(self):
        self.logic = LikesLogic()

    # like vacation when liked / unlike vacation when not liked
    def like(self, vacation_id):
        AuthFacade().block_anonymous()
        self.logic.like(g.current_user["id"], vacation_id)

