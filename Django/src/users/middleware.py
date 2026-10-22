from django.http import JsonResponse
from rest_framework import status
from utils.app_config import AppConfig
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError, InvalidSignatureError, InvalidAudienceError, InvalidIssuerError, ImmatureSignatureError, MissingRequiredClaimError, PyJWTError

# Define all PyJWT Exceptions as tuple
JWT_ERRORS = (InvalidTokenError, DecodeError, InvalidSignatureError,
              InvalidAudienceError, InvalidIssuerError, ImmatureSignatureError, MissingRequiredClaimError, PyJWTError)


def fix_response_middleware(get_response):
    """Middleware that fixes and renders all responses"""
    def middleware(request):
        try:
            response = get_response(request)
            return response
        except Exception as e:
            # Return a simple JSON response for any errors
            return JsonResponse({"error": str(e)}, status=500)
    
    return middleware


def auth_middleware(get_response):

    def middleware(request):
        # Skip auth check for these paths
        public_paths = ["/", "/api/auth/login", "/api/auth/refresh-token", "/api/auth/logout"]
        
        if request.path not in public_paths:
            token = request.headers.get("Authorization")
            if not token:
                return JsonResponse({"error": "Unauthorized"}, status=401)
            
            try:
                header_data = jwt.get_unverified_header(token)
                decoded = jwt.decode(
                    token, AppConfig.secret_key, audience=AppConfig.audience, algorithms=[header_data["alg"]])
                # Check if token type is access
                if decoded.get("type") != "access":
                    return JsonResponse({"error": "Unauthorized"}, status=401)
            except ExpiredSignatureError:
                refresh_cookie = request.COOKIES.get("refresh")
                if not refresh_cookie:
                    return JsonResponse({"error": "Unauthorized"}, status=401)
                return JsonResponse({"error": "Token expired, refresh required"}, status=406)
            except JWT_ERRORS:
                return JsonResponse({"error": "Unauthorized"}, status=401)
            except Exception as err:
                return JsonResponse({"error": str(err)}, status=500)
        
        response = get_response(request)
        return response

    return middleware
