from re import match
from .role_model import RoleModel

class UserModel:
    def __init__(self, id, first_name, last_name, email, password, role):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.password = password
        self.role = role

    def validate_insert(self):
        if not self.first_name:
            return "Missing first name."
        if not self.last_name:
            return "Missing last name."
        if not self.email:
            return "Missing email."
        if not self.password:
            return "Missing password."
        if not self.role:
            return "Missing role."
        if not 2 <= len(self.first_name) <= 15:
            return "First name length should be 2-15 characters."
        # Check last name
        if not 2 <= len(self.last_name) <= 15:
            return "Last name length should be 2-15 characters."
        # Check email
        if not 6 <= len(self.email) <= 30:
            return "Email length must be 6 to 30 characters."
        if not match(r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$", self.email):
            return "Entered invalid email."
        # Check password
        if len(self.password) < 4:
            return "Entered too short password."
        if len(self.password) > 32:
            return "Password length must be 4 to 32 characters."
        if self.role != RoleModel.User.value:
            return "This role unacceptable"
        return None
