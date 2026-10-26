from utils.errors import server_error
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.db.models import Count, F
from .models import LikeModel, LikesSerializer


@api_view(["GET"])
def total_likes(request):
    try:
        json = {
            "total_likes": LikeModel.objects.all().count()
        }
        return Response(json)
    except Exception:
        return server_error(request)

# -------------------------------------------------------


@api_view(["GET"])
def likes_statistics(request):
    try:
        likes_statistics = LikeModel.objects.values(destination=F(
            "vacation__country__name")).annotate(likes=Count('vacation_id'))
        serializer = LikesSerializer(likes_statistics, many=True)
        return Response(serializer.data)
    except Exception:
        return server_error(request)
