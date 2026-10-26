from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from .models import UserModel
from utils.security import Security
from django.db import transaction
from utils import auth_status


class AuthBackend(ModelBackend):
    @transaction.atomic
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = UserModel.objects.select_for_update().get(email=username)
            # Check password matches
            if auth_status.is_enabled(auth_status.get_status(user.pk)) and Security.verify(password, user.password):
                if Security.needs_rehash(user.password):
                    user.password = Security.hash(password)
                    user.save(update_fields=["password"])
                return user
            return None
        except UserModel.DoesNotExist:
            return None
