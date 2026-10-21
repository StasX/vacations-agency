from django.contrib import admin
from django.urls import path, include, re_path
from .views import logout, login, refresh_token, catch_all, health_check

urlpatterns = [
    path('', health_check, name='health_check'),  # Root endpoint
    path('admin/', admin.site.urls),
    path("api/auth/login", login),
    path("api/auth/logout", logout),
    path("api/auth/refresh-token", refresh_token),
    path("api/vacations/", include("vacations.urls")),
    path("api/users/", include("users.urls")),
    path("api/likes/", include("likes.urls")),
    re_path(r'^api/.*', catch_all),  # Catch-all for API routes
    re_path(r'^.*$', health_check),  # Fallback for all other routes
]
