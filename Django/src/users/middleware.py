from django.http import JsonResponse
from rest_framework import status
from utils.app_config import AppConfig
from utils.tokens import decode_token
from utils.errors import server_error
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
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
        # Skip auth check for these paths
        public_paths = ["/", "/api/auth/csrf", "/api/auth/login", "/api/auth/refresh-token", "/api/auth/logout"]
        
        if request.path not in public_paths:
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
            except ExpiredSignatureError:
                refresh_cookie = request.COOKIES.get("refresh")
                if not refresh_cookie:
                    return JsonResponse({"error": "Unauthorized"}, status=401)
                return JsonResponse({"error": "Token expired, refresh required"}, status=406)
            except JWT_ERRORS:
                return JsonResponse({"error": "Unauthorized"}, status=401)
            except Exception:
                return server_error(request)
        
        response = get_response(request)
        return response

    return middleware
