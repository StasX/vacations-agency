from django.db.models import Model, CharField, ForeignKey, DO_NOTHING


class RoleModel(Model):
    role_type = CharField(max_length=20)

    class Meta:
        db_table = 'roles'
# ------------------------------------------------------------------------------------------


class UserModel(Model):
    first_name = CharField(max_length=15)
    last_name = CharField(max_length=15)
    email = CharField(unique=True, max_length=30)
    password = CharField(max_length=128)
    role = ForeignKey(RoleModel, DO_NOTHING)

    class Meta:
        db_table = 'users'
