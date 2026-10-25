from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from utils.app_config import AppConfig
from django.contrib.auth import authenticate
import jwt
from datetime import timedelta, datetime
from users.models import UserModel
from uuid import uuid4
from jwt import ExpiredSignatureError, InvalidTokenError, DecodeError, InvalidSignatureError, InvalidAudienceError, InvalidIssuerError, ImmatureSignatureError, MissingRequiredClaimError, PyJWTError

# Define all PyJWT Exceptions as tuple (Make it available for all views in this script)
JWT_ERRORS = (ExpiredSignatureError, InvalidTokenError, DecodeError, InvalidSignatureError,
              InvalidAudienceError, InvalidIssuerError, ImmatureSignatureError, MissingRequiredClaimError, PyJWTError)


def health_check(request):
    """Health check endpoint - returns plain JSON"""
    if request.method == 'GET':
        return JsonResponse({"status": "OK"})
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def login(request):
    """Login endpoint"""
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")
        
        credentials = {
            "username": email,
            "password": password,
        }
        user = authenticate(request, **credentials)
        if not user:
            return JsonResponse({"error": "Wrong credentials"}, status=400)
        # Set access payload
        access_payload = {
            'type': 'access',
            'user': {
                'id': user.id,
                'firstName': user.first_name,
                'lastName': user.last_name,
                'email': user.email,
                'role': user.role.role_type,
            },
            'exp': datetime.utcnow() + timedelta(minutes=10),
            'iat': datetime.utcnow(),
            'iss': AppConfig.issuer,
            'aud': AppConfig.audience,
            'jti': str(uuid4())
        }
        # Set refresh payload
        refresh_payload = access_payload.copy()
        refresh_payload["type"] = "refresh"
        refresh_payload["jti"] = str(uuid4())
        refresh_payload["exp"] = datetime.utcnow() + timedelta(hours=1)
        # Create tokens
        access_token = jwt.encode(
            access_payload, key=AppConfig.secret_key, algorithm="HS256")
        refresh_token = jwt.encode(
            refresh_payload, key=AppConfig.secret_key, algorithm="HS256")
        # Create response with plain JSON
        response = JsonResponse({"access_token": access_token}, status=200)
        response.set_cookie(key="refresh", value=refresh_token,
                            httponly=True, secure=True, samesite="lax", max_age=60*60)
        return response
    except Exception as err:
        return JsonResponse({"error": str(err)}, status=500)


# -------------------------------------------------------


@csrf_exempt
def logout(request):
    """Logout endpoint"""
    if request.method != 'DELETE':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        response = JsonResponse({}, status=204)
        # remove the cookies if exists
        cookie = request.COOKIES.get("refresh")
        if cookie:
            response.delete_cookie("refresh")
        return response
    except JWT_ERRORS:
        return JsonResponse({"error": "Bad Request"}, status=400)
    except Exception as err:
        return JsonResponse({"error": str(err)}, status=500)


# -------------------------------------------------------


@csrf_exempt
def refresh_token(request):
    """Refresh token endpoint"""
    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        # remove the cookie if exists
        refresh_cookie = request.COOKIES.get("refresh")
        # If cookie not exists user unauthorized
        if not refresh_cookie:
            return JsonResponse({"error": "Unauthorized"}, status=401)
        header_data = jwt.get_unverified_header(refresh_cookie)
        decoded = jwt.decode(refresh_cookie, AppConfig.secret_key,
                             audience=AppConfig.audience,  algorithms=[header_data["alg"]])
        if decoded.get("type") != "refresh":
            return JsonResponse({"error": "Unauthorized"}, status=401)

        access_payload = decoded.copy()
        access_payload["type"] = "access"
        access_payload["exp"] = datetime.utcnow() + timedelta(minutes=10)
        access_payload["iat"] = datetime.utcnow()
        access_payload["iss"] = AppConfig.issuer
        access_payload["aud"] = AppConfig.audience
        access_payload["jti"] = str(uuid4())

        refresh_payload = access_payload.copy()
        refresh_payload["type"] = "refresh"
        refresh_payload["exp"] = datetime.utcnow() + timedelta(hours=1)
        refresh_payload["iat"] = datetime.utcnow()
        refresh_payload["jti"] = str(uuid4())
        # Create tokens
        access_token = jwt.encode(
            access_payload, key=AppConfig.secret_key, algorithm="HS256")
        refresh_token_new = jwt.encode(
            refresh_payload, key=AppConfig.secret_key, algorithm="HS256")
        # Create response with plain JSON
        response = JsonResponse({"access_token": access_token}, status=200)
        response.set_cookie(key="refresh", value=refresh_token_new,
                            httponly=True, secure=True, samesite="lax", max_age=60*60*10)
        return response
    except JWT_ERRORS as err:
        print("------------------------------------------------------")
        print(err)
        print("------------------------------------------------------")
        return JsonResponse({"error": "Unauthorized"}, status=401)
    except Exception as err:
        print("------------------------------------------------------")
        print(err)
        print("------------------------------------------------------")
        return JsonResponse({"error": str(err)}, status=500)


@csrf_exempt
def catch_all(request):
    """Catch-all view for unmatched routes"""
    return JsonResponse({"error": "Not Found"}, status=404)
