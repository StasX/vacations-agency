from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone


pytestmark = pytest.mark.django_db


def sign_in(client, user):
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    assert response.status_code == 200
    return response.json()['access_token'], response.cookies['refresh'].value


def test_refresh_replay_revokes_refresh_family_but_access_is_stateless(client, user):
    access, original = sign_in(client, user)
    rotated = client.post('/api/auth/refresh-token')
    assert rotated.status_code == 200
    assert rotated.cookies['refresh'].value != original
    newest = rotated.cookies['refresh'].value
    client.cookies['refresh'] = original
    assert client.post('/api/auth/refresh-token').status_code == 401
    client.cookies['refresh'] = newest
    assert client.post('/api/auth/refresh-token').status_code == 401
    assert client.get('/api/users/total', HTTP_AUTHORIZATION=access).status_code == 200


def test_logout_clears_cookie_without_database_access(client, user, django_assert_num_queries):
    access, refresh = sign_in(client, user)
    with django_assert_num_queries(0):
        response = client.delete('/api/auth/logout')
    assert response.status_code == 204 and response.content == b''
    cookie = response.cookies['refresh']
    assert cookie['path'] == '/' and cookie['max-age'] == 0
    assert cookie['secure'] and cookie['httponly'] and cookie['samesite'] == 'Lax'
    # Access tokens stay stateless; refresh tokens are revoked in Redis.
    assert client.get('/api/users/total', HTTP_AUTHORIZATION=access).status_code == 200
    client.cookies['refresh'] = refresh
    assert client.post('/api/auth/refresh-token').status_code == 401
    assert client.delete('/api/auth/logout').status_code == 204


def test_access_validation_does_not_query_database_or_redis(client, user, django_assert_num_queries, monkeypatch):
    from django.http import JsonResponse
    from django.test import RequestFactory
    from users.middleware import auth_middleware
    access, _ = sign_in(client, user)
    def unexpected_redis():
        pytest.fail('Access validation must not read Redis')
    monkeypatch.setattr('utils.refresh_tokens.get_redis', unexpected_redis)
    request = RequestFactory().get('/api/users/total', HTTP_AUTHORIZATION=access)
    with django_assert_num_queries(0):
        response = auth_middleware(lambda request: JsonResponse({'ok': True}))(request)
    assert response.status_code == 200


@pytest.mark.parametrize('change', ['password', 'role', 'deleted'])
def test_refresh_rechecks_current_user(client, user, change):
    sign_in(client, user)
    if change == 'password':
        user.password = 'changed-password-hash'
        user.save(update_fields=['password'])
    elif change == 'role':
        user.role.role_type = 'User'
        user.role.save()
    else:
        user.delete()
    assert client.post('/api/auth/refresh-token').status_code == 401


def test_refresh_uses_current_profile(client, user):
    from utils.tokens import decode_token
    sign_in(client, user)
    user.first_name = 'Updated'
    user.save(update_fields=['first_name'])
    response = client.post('/api/auth/refresh-token')
    assert decode_token(response.json()['access_token'])['user']['firstName'] == 'Updated'


def test_refresh_expiry_is_absolute(client, user):
    from utils.tokens import decode_token, issue_tokens
    expiry = timezone.now() + timedelta(seconds=90)
    _, refresh, _ = issue_tokens(user, expiry)
    from utils.refresh_tokens import register
    register(refresh)
    client.cookies['refresh'] = refresh
    response = client.post('/api/auth/refresh-token')
    assert response.status_code == 200
    assert decode_token(response.cookies['refresh'].value)['exp'] == int(expiry.timestamp())
    assert 0 < response.cookies['refresh']['max-age'] <= 90


def test_failed_refresh_can_be_retried(client, user, monkeypatch):
    sign_in(client, user)
    with monkeypatch.context() as patch:
        def fail(*args):
            raise RuntimeError('signing unavailable')
        patch.setattr('api.views.issue_tokens', fail)
        assert client.post('/api/auth/refresh-token').status_code == 500
    assert client.post('/api/auth/refresh-token').status_code == 200


def test_refresh_get_cannot_issue_tokens(client, user):
    sign_in(client, user)
    response = client.get('/api/auth/refresh-token')
    assert response.status_code == 405
    assert 'refresh' not in response.cookies


@pytest.mark.parametrize('path,method', [('/api/auth/login', 'post'),
    ('/api/auth/refresh-token', 'post'), ('/api/auth/logout', 'delete')])
@pytest.mark.parametrize('defect', ['missing', 'invalid', 'foreign-origin'])
def test_auth_requires_csrf_and_trusted_origin(user, path, method, defect):
    client = Client(enforce_csrf_checks=True)
    token = client.get('/api/auth/csrf', secure=True).json()['csrf_token']
    headers = {'HTTP_ORIGIN': 'https://testserver'}
    if defect != 'missing':
        headers['HTTP_X_CSRFTOKEN'] = token if defect == 'foreign-origin' else 'invalid'
    if defect == 'foreign-origin':
        headers['HTTP_ORIGIN'] = 'https://attacker.example'
    response = getattr(client, method)(path, secure=True, **headers)
    assert response.status_code == 403
    assert response.json() == {'error': 'CSRF verification failed'}
    assert 'refresh' not in response.cookies


def test_complete_csrf_protected_lifecycle(user):
    client = Client(enforce_csrf_checks=True)
    def options():
        response = client.get('/api/auth/csrf', secure=True)
        assert response.cookies['csrftoken']['secure']
        assert response.cookies['csrftoken']['httponly']
        assert 'no-store' in response['Cache-Control']
        return {'secure': True, 'HTTP_ORIGIN': 'https://testserver',
                'HTTP_X_CSRFTOKEN': response.json()['csrf_token']}

    old_options = options()
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json', **old_options)
    assert response.status_code == 200
    assert 'no-store' in response['Cache-Control']
    # Successful login rotates the CSRF secret.
    assert client.post('/api/auth/refresh-token', **old_options).status_code == 403
    assert client.post('/api/auth/refresh-token', **options()).status_code == 200
    assert client.delete('/api/auth/logout', **options()).status_code == 204


def test_non_admin_cannot_create_dashboard_session(client, user):
    user.role.role_type = 'User'
    user.role.save()
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    assert response.status_code == 403
    assert 'refresh' not in response.cookies
