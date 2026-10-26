from utils.dal import *
from models.user_model import *


class AuthLogic:
    def __init__(self):
        self.dal = DAL()

    def add_user(self, user):
        sql = "INSERT INTO users (first_name, last_name, email, password, role_id) VALUES (%s,%s,%s,%s,%s)"
        params = (user.first_name, user.last_name, user.email, user.password, user.role)
        last_inserted_id = self.dal.insert(sql, params)
        return last_inserted_id

    def get_user(self, credentials, for_update=False):
        sql = "SELECT id, first_name, last_name, email, password, role_id AS role FROM users WHERE email=%s"
        if for_update:
            sql += " FOR UPDATE"
        params = (credentials.email,)
        user = self.dal.get_scalar(sql, params)
        return user

    def update_password(self, user_id, password_hash):
        return self.dal.update("UPDATE users SET password=%s WHERE id=%s", (password_hash, user_id))

    def is_email_exists(self, email):
        sql = "SELECT COUNT(*) FROM users WHERE email = %s"
        params = (email,)
        result = self.dal.get_scalar(sql, params)
        return result and result.get('COUNT(*)') == 1

    def close(self):
        self.dal.close()
