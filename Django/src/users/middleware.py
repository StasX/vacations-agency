from django.http import JsonResponse
from rest_framework import status
from utils.app_config import AppConfig
from utils.tokens import decode_token, password_fingerprint
from django.utils.crypto import constant_time_compare
from users.models import UserModel
from utils.errors import server_error
from utils import auth_status
from redis.exceptions import RedisError
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
from django.urls import resolve, Resolver404
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError, InvalidSignatureError, InvalidAudienceError, InvalidIssuerError, ImmatureSignatureError, MissingRequiredClaimError, PyJWTError

# Define all PyJWT Exceptions as tuple
JWT_ERRORS = (InvalidTokenError, DecodeError, InvalidSignatureError,
              InvalidAudienceError, InvalidIssuerError, ImmatureSignatureError, MissingRequiredClaimError, PyJWTError)


def fix_response_middleware(get_response):
    """Handle unexpected view errors through Django's exception middleware hook."""
    def process_exception(request, exception):
        if isinstance(exception, (Http404, PermissionDenied, SuspiciousOperation)):
            return None
        return server_error(request)

    def middleware(request):
        try:
            response = get_response(request)
            return response
        except (Http404, PermissionDenied, SuspiciousOperation):
            raise
        except Exception:
            return server_error(request)
    
    middleware.process_exception = process_exception
    return middleware


def auth_middleware(get_response):

    def middleware(request):
        # Authenticate resolved statistics views; admin owns its authentication.
        try:
            view = resolve(request.path_info).func
        except Resolver404:
            return get_response(request)
        if view.__module__ in {"users.views", "likes.views", "vacations.views"}:
            token = request.headers.get("Authorization")
            if not token:
                return JsonResponse({"error": "Unauthorized"}, status=401)
            
            try:
                decoded = decode_token(token)
                # Check if token type is access
                if decoded.get("type") != "access":
                    return JsonResponse({"error": "Unauthorized"}, status=401)
                user = decoded.get("user")
                if not isinstance(user, dict) or user.get("role") != "Admin":
                    return JsonResponse({"error": "Forbidden"}, status=403)
                if type(user.get("id")) is not int or user["id"] <= 0:
                    return JsonResponse({"error": "Unauthorized"}, status=401)
                current = UserModel.objects.select_related('role').filter(pk=user['id']).first()
                fingerprint = decoded.get('pwd')
                status = auth_status.get_status(user['id'])
                if (current is None or not auth_status.is_enabled(status)
                        or decoded.get('auth_status') != status
                        or current.role.role_type != 'Admin'
                        or not isinstance(fingerprint, str)
                        or not constant_time_compare(fingerprint, password_fingerprint(current))):
                    return JsonResponse({"error": "Unauthorized"}, status=401)
            except ExpiredSignatureError:
                refresh_cookie = request.COOKIES.get("refresh")
                if not refresh_cookie:
                    return JsonResponse({"error": "Unauthorized"}, status=401)
                return JsonResponse({"error": "Token expired, refresh required"}, status=406)
            except JWT_ERRORS:
                return JsonResponse({"error": "Unauthorized"}, status=401)
            except RedisError:
                response = JsonResponse({"error": "Authentication temporarily unavailable"}, status=503)
                response['Retry-After'] = '5'
                return response
            except Exception:
                return server_error(request)
        
        response = get_response(request)
        return response

    return middleware
