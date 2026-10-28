import json
import logging
from datetime import datetime, timezone as datetime_timezone

import jwt
from redis.exceptions import RedisError
from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token, rotate_token
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect

from users.models import UserModel
from utils import refresh_tokens, auth_status
from utils.tokens import issue_tokens, password_fingerprint
from utils.errors import server_error
from utils.tokens import decode_token


def health(request):
    return HttpResponse(status=200)


def health_check(request):
    if request.method == 'GET':
        return JsonResponse({'status': 'OK'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def csrf_failure(request, reason=''):
    return JsonResponse({'error': 'CSRF verification failed'}, status=403)


@never_cache
@ensure_csrf_cookie
def csrf_token(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    return JsonResponse({'csrf_token': get_token(request)})


def clear_refresh(response):
    response.delete_cookie('refresh', path='/', samesite='Lax')
    # Keep deletion attributes aligned with issuance (including Secure).
    response.cookies['refresh']['secure'] = settings.AUTH_COOKIE_SECURE
    response.cookies['refresh']['httponly'] = True
    return response


def redis_unavailable():
    logging.getLogger(__name__).exception('Refresh token store unavailable')
    response = JsonResponse({'error': 'Authentication temporarily unavailable'}, status=503)
    response['Retry-After'] = '5'
    return response


def unauthorized():
    return clear_refresh(JsonResponse({'error': 'Unauthorized'}, status=401))


def token_response(user, expires_at=None, previous=None, expected_status=None):
    access, refresh, expires_at = issue_tokens(user, expires_at)
    status = decode_token(access).get('auth_status')
    if (not auth_status.is_enabled(status)
            or (expected_status is not None and status != expected_status)):
        return unauthorized()
    stored = refresh_tokens.rotate(previous, refresh) if previous else refresh_tokens.register(refresh)
    if not stored:
        return unauthorized()
    response = JsonResponse({'access_token': access})
    response.set_cookie('refresh', refresh, path='/', httponly=True,
                        secure=settings.AUTH_COOKIE_SECURE, samesite='Lax',
                        max_age=max(0, int(expires_at.timestamp()) - int(timezone.now().timestamp())))
    return response


@never_cache
@csrf_protect
def login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        try:
            data = json.loads(request.body)
        except (ValueError, UnicodeError):
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
        email, password = data.get('email'), data.get('password')
        if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password:
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
        user = authenticate(request, username=email, password=password)
        if not user:
            return JsonResponse({'error': 'Wrong credentials'}, status=400)
        if user.role.role_type != 'Admin':
            return JsonResponse({'error': 'Forbidden'}, status=403)
        previous = request.COOKIES.get('refresh')
        if previous:
            try:
                refresh_tokens.revoke(previous)
            except jwt.InvalidTokenError:
                pass
        response = token_response(user)
        rotate_token(request)
        return response
    except RedisError:
        return redis_unavailable()
    except Exception:
        return server_error(request)


@never_cache
@csrf_protect
def logout(request):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        cookie = request.COOKIES.get('refresh')
        if cookie:
            try:
                refresh_tokens.revoke(cookie)
            except jwt.InvalidTokenError:
                pass
        rotate_token(request)
        return clear_refresh(HttpResponse(status=204))
    except RedisError:
        return redis_unavailable()
    except Exception:
        return server_error(request)


@never_cache
@csrf_protect
def refresh_token(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        cookie = request.COOKIES.get('refresh')
        if not cookie:
            return unauthorized()
        claims = decode_token(cookie)
        if claims.get('type') != 'refresh':
            return unauthorized()
        profile = claims.get('user')
        if not isinstance(profile, dict) or type(profile.get('id')) is not int or profile['id'] <= 0:
            return unauthorized()
        try:
            user = UserModel.objects.select_related('role').get(pk=profile['id'])
        except UserModel.DoesNotExist:
            refresh_tokens.revoke(cookie)
            return unauthorized()
        status = auth_status.get_status(user.pk)
        if (not auth_status.is_enabled(status) or claims.get('auth_status') != status
                or user.role.role_type != 'Admin' or claims.get('pwd') != password_fingerprint(user)):
            refresh_tokens.revoke(cookie)
            return unauthorized()
        # Preserve the original refresh deadline; refreshing cannot extend it.
        expires_at = datetime.fromtimestamp(claims['exp'], tz=datetime_timezone.utc)
        return token_response(user, expires_at, previous=cookie, expected_status=status)
    except jwt.InvalidTokenError:
        return unauthorized()
    except RedisError:
        return redis_unavailable()
    except Exception:
        return server_error(request)


def catch_all(request):
    return JsonResponse({'error': 'Not Found'}, status=404)
