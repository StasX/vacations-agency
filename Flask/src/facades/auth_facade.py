from flask import session, request
from logic.auth_logic import AuthLogic
from models.credentials_model import CredentialsModel
from models.user_model import UserModel
from models.role_model import RoleModel
from models.client_errors import ValidationError, AuthError
from utils.security import Security


class AuthFacade:
    def __init__(self):
        self.logic = AuthLogic()

    # Login
    def login(self):
        email = request.form.get("email")
        password = request.form.get("password")
        credentials = CredentialsModel(email, password)
        error = credentials.validate()
        if error:
            raise ValidationError(error, credentials)
        credentials.password = Security.hash(credentials.password)
        user = self.logic.get_user(credentials)
        if not user:
            raise AuthError("Invalid email or password.", credentials)
        del user["password"]
        session["current_user"] = user

    # Register
    def register(self):
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        password = request.form.get("password")
        user = UserModel(None, first_name, last_name, email,
                         password, RoleModel.User.value)
        error = user.validate_insert()
        if error:
            raise ValidationError(error, user)
        if self.logic.is_email_exists(email):
            raise ValidationError("Email already exists.", user)
        user.password = Security.hash(user.password)
        self.logic.add_user(user)
        user = self.logic.get_user(user)
        del user["password"]
        session["current_user"] = user

    def logout(self):
        session.clear()

    # Block non logged-in users: 
    def block_anonymous(self):
        user = session.get("current_user")
        if not user: raise AuthError("You are not logged-in.")

    # Block non admin users: 
    def block_non_admin(self):
        user = session.get("current_user")
        if not user: raise AuthError("You are not logged-in.")
        if user["role"] != RoleModel.Admin.value: raise AuthError("You are not authorized.")
