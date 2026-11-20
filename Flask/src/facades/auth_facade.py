from flask import g, request
from logic.auth_logic import AuthLogic
from models.credentials_model import CredentialsModel
from models.user_model import UserModel
from models.role_model import RoleModel
from models.client_errors import ValidationError, AuthError
from utils.security import Security
from utils import auth_status, auth_token
from hmac import compare_digest


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
                user['password'] = Security.hash(password)
                self.logic.update_password(user["id"], user['password'])
        return auth_token.issue_token(user, status)

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
            status = auth_status.initialize_status(user['id'])
            if not auth_status.is_enabled(status):
                raise AuthError("Account disabled.")
        return auth_token.issue_token(user, status)

    # Block non logged-in users: 
    def block_anonymous(self):
        if "current_user" not in g:
            g.current_user = self.check_status()

    # Block non admin users: 
    def block_non_admin(self):
        self.block_anonymous()
        if g.current_user["role"] != RoleModel.Admin.value:
            raise AuthError("You are not authorized.")

    @staticmethod
    def check_status():
        claims = auth_token.get_claims()
        if claims is None:
            raise AuthError("You are not logged-in.")
        user_id = int(claims["sub"])
        status = auth_status.get_status(user_id)
        if status != claims["status"] or not auth_status.is_enabled(status) or auth_token.is_revoked(claims):
            auth_token.clear_claims()
            raise AuthError("Your login is no longer valid.")
        logic = AuthLogic()
        try:
            current = logic.get_user_by_id(user_id)
        finally:
            logic.close()
        if (not current or current["role"] != claims["role"]
                or not compare_digest(claims["pwd"], Security.password_fingerprint(current["password"]))):
            auth_token.clear_claims()
            raise AuthError("Your login is no longer valid.")
        return {key: value for key, value in current.items() if key != "password"}
