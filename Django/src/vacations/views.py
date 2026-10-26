from utils.errors import server_error
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import VacationModel
from datetime import date


@api_view(["GET"])
# @permission_classes([IsAuthenticated])
def vacations_statistics(request):
    try:
        today = date.today()
        json = {
            "past_vacations": VacationModel.objects.filter(end_date__lt=today).count(),
            "on_going_vacations": VacationModel.objects.filter(start_date__lte=today, end_date__gte=today).count(),
            "future_vacations": VacationModel.objects.filter(start_date__gt=today).count(),
        }
        return Response(json)

    except Exception:
        return server_error(request)

# -------------------------------------------------------
