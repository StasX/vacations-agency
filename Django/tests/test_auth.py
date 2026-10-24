from datetime import datetime, timedelta, timezone

import jwt
import pytest
from django.contrib.auth import authenticate
from utils.app_config import AppConfig


def decode(token):
    return jwt.decode(token, AppConfig.secret_key, algorithms=['HS256'],
                      audience=AppConfig.audience, issuer=AppConfig.issuer)


@pytest.mark.django_db
def test_login_issues_signed_tokens(client, user):
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    assert response.status_code == 200
    access = decode(response.json()['access_token'])
    refresh = decode(response.cookies['refresh'].value)
    assert access['type'] == 'access'
    assert access['user'] == dict(id=user.id, firstName='Test', lastName='Admin',
                                  email=user.email, role='Admin')
    assert refresh['type'] == 'refresh'
    assert refresh['jti'] != access['jti']
    assert access['exp'] - access['iat'] == 600
    assert refresh['exp'] - refresh['iat'] == 3600
    cookie = response.cookies['refresh']
    assert cookie['httponly'] and cookie['secure']
    assert cookie['samesite'] == 'lax'
    assert cookie['max-age'] == 3600


@pytest.mark.django_db
@pytest.mark.parametrize('email,password', [('unknown@example.com', 'Password123!'),
                                          ('admin@example.com', 'wrong')])
def test_wrong_credentials(client, user, email, password):
    response = client.post('/api/auth/login', dict(email=email, password=password),
                           content_type='application/json')
    assert response.status_code == 400
    assert response.json() == {'error': 'Wrong credentials'}
    assert 'refresh' not in response.cookies


@pytest.mark.django_db
def test_auth_backend(user):
    assert authenticate(username=user.email, password='Password123!') == user
    assert authenticate(username=user.email, password='wrong') is None
    assert authenticate(username='missing@example.com', password='wrong') is None


@pytest.mark.parametrize('path,method', [('/api/auth/login', 'get'),
    ('/api/auth/logout', 'post'), ('/api/auth/refresh-token', 'post')])
def test_auth_methods(client, path, method):
    assert getattr(client, method)(path).status_code == 405


def test_refresh_rotates_tokens(client, token_factory):
    old = token_factory(type='refresh')
    client.cookies['refresh'] = old
    response = client.get('/api/auth/refresh-token')
    assert response.status_code == 200
    access = decode(response.json()['access_token'])
    refresh = decode(response.cookies['refresh'].value)
    assert access['type'] == 'access'
    assert refresh['type'] == 'refresh'
    assert access['user'] == decode(old)['user']
    assert len({access['jti'], refresh['jti'], decode(old)['jti']}) == 3


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'expired', 'wrong-audience', 'wrong-key'])
def test_refresh_rejects_invalid_cookie(client, token_factory, kind):
    if kind == 'malformed':
        client.cookies['refresh'] = 'not-a-jwt'
    elif kind == 'expired':
        client.cookies['refresh'] = token_factory(type='refresh', exp=datetime.now(timezone.utc)-timedelta(seconds=1))
    elif kind == 'wrong-audience':
        client.cookies['refresh'] = token_factory(type='refresh', aud='other')
    elif kind == 'wrong-key':
        client.cookies['refresh'] = jwt.encode(decode(token_factory()), 'another-key', algorithm='HS256')
    response = client.get('/api/auth/refresh-token')
    assert response.status_code == 401
    assert response.json() == {'error': 'Unauthorized'}


@pytest.mark.parametrize('has_cookie', [False, True])
def test_logout(client, has_cookie):
    if has_cookie:
        client.cookies['refresh'] = 'old-token'
    response = client.delete('/api/auth/logout')
    assert response.status_code == 204
    if has_cookie:
        assert response.cookies['refresh']['max-age'] == 0


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Known bug: refresh accepts access tokens')
def test_refresh_rejects_access_token(client, token_factory):
    client.cookies['refresh'] = token_factory()
    assert client.get('/api/auth/refresh-token').status_code == 401


@pytest.mark.parametrize('body', ['{', '[]', 'null'])
@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Known bug: invalid login JSON returns 500')
def test_invalid_login_input_returns_400(client, body):
    assert client.post('/api/auth/login', body, content_type='application/json').status_code == 400


@pytest.mark.django_db
@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Known bug: missing password returns 500')
def test_missing_password_returns_400(client, user):
    response = client.post('/api/auth/login', {'email': user.email}, content_type='application/json')
    assert response.status_code == 400


def test_refresh_unexpected_failure_returns_500(client, token_factory, monkeypatch):
    client.cookies['refresh'] = token_factory(type='refresh')
    def fail(*args, **kwargs):
        raise RuntimeError('token service unavailable')
    monkeypatch.setattr('api.views.jwt.encode', fail)
    assert client.get('/api/auth/refresh-token').status_code == 500
