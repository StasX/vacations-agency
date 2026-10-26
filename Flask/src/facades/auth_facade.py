from flask import session, request
from logic.auth_logic import AuthLogic
from models.credentials_model import CredentialsModel
from models.user_model import UserModel
from models.role_model import RoleModel
from models.client_errors import ValidationError, AuthError
from utils.security import Security
from utils import auth_status


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
        with self.logic.dal.transaction():
            user = self.logic.get_user(credentials, for_update=True)
            if not user or not Security.verify(password, user["password"]):
                raise AuthError("Invalid email or password.", credentials)
            status = auth_status.get_status(user['id'])
            if not auth_status.is_enabled(status):
                raise AuthError("Invalid email or password.", credentials)
            if Security.needs_rehash(user["password"]):
                self.logic.update_password(user["id"], Security.hash(password))
        del user["password"]
        session.clear()
        session["current_user"] = user
        session['auth_status'] = status

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
        password_hash = Security.hash(user.password)
        with self.logic.dal.transaction():
            if self.logic.is_email_exists(email):
                raise ValidationError("Email already exists.", user)
            user.password = password_hash
            self.logic.add_user(user)
            user = self.logic.get_user(user)
            if user is None:
                raise RuntimeError("Registered account could not be read back")
            status = auth_status.get_status(user['id'])
            if not auth_status.is_enabled(status):
                raise AuthError("Account disabled.")
        del user["password"]
        session.clear()
        session["current_user"] = user
        session['auth_status'] = status

    def logout(self):
        session.clear()

    # Block non logged-in users: 
    def block_anonymous(self):
        user = session.get("current_user")
        if not user: raise AuthError("You are not logged-in.")
        self.check_status(user)

    # Block non admin users: 
    def block_non_admin(self):
        user = session.get("current_user")
        if not user: raise AuthError("You are not logged-in.")
        self.check_status(user)
        if user["role"] != RoleModel.Admin.value: raise AuthError("You are not authorized.")

    @staticmethod
    def check_status(user):
        status = auth_status.get_status(user['id'])
        if not auth_status.is_enabled(status) or session.get('auth_status', 'enabled:initial') != status:
            session.clear()
            raise AuthError("Your session is no longer valid.")
