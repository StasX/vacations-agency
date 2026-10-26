from django.db.models import Model, ForeignKey, DO_NOTHING, CompositePrimaryKey
from users.models import UserModel
from vacations.models import VacationModel
from rest_framework.serializers import Serializer, CharField, IntegerField


class LikeModel(Model):

    pk = CompositePrimaryKey('user_id', 'vacation_id')
    user = ForeignKey(UserModel, DO_NOTHING)
    vacation = ForeignKey(VacationModel, DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'likes'


# ------------------------------------------------------------------------------------------

class LikesSerializer(Serializer):
    destination = CharField()
    likes = IntegerField()
