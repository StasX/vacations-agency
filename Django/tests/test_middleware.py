from datetime import datetime, timedelta, timezone

import jwt
import pytest
from django.http import JsonResponse
from django.test import RequestFactory
from users.middleware import auth_middleware, fix_response_middleware

PROTECTED = ['/api/users/total', '/api/likes/total', '/api/likes/statistics',
             '/api/vacations/statistics', '/admin/']


@pytest.mark.parametrize('path', PROTECTED)
def test_missing_token_denied(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json() == {'error': 'Unauthorized'}


@pytest.mark.parametrize('kind', ['malformed', 'refresh', 'expired', 'wrong-audience', 'wrong-key'])
def test_invalid_access_denied(client, token_factory, kind):
    tokens = {
        'malformed': 'broken', 'refresh': token_factory(type='refresh'),
        'expired': token_factory(exp=datetime.now(timezone.utc)-timedelta(seconds=1)),
        'wrong-audience': token_factory(aud='other'),
        'wrong-key': jwt.encode({'type': 'access'}, 'wrong-key', algorithm='HS256'),
    }
    assert client.get('/api/users/total', HTTP_AUTHORIZATION=tokens[kind]).status_code == 401


def test_expired_access_requests_refresh(client, token_factory):
    client.cookies['refresh'] = token_factory(type='refresh')
    response = client.get('/api/users/total', HTTP_AUTHORIZATION=token_factory(
        exp=datetime.now(timezone.utc)-timedelta(seconds=1)))
    assert response.status_code == 406
    assert response.json() == {'error': 'Token expired, refresh required'}


def test_valid_token_calls_downstream(token_factory):
    request = RequestFactory().get('/api/users/total', HTTP_AUTHORIZATION=token_factory())
    response = JsonResponse({'called': True})
    assert auth_middleware(lambda req: response)(request) is response


def test_response_wrapper_handles_exception():
    def fail(request):
        raise ValueError('downstream failure')
    response = fix_response_middleware(fail)(RequestFactory().get('/'))
    assert response.status_code == 500
    assert b'downstream failure' in response.content


def test_response_wrapper_preserves_response():
    response = JsonResponse({'ok': True}, status=201)
    assert fix_response_middleware(lambda req: response)(RequestFactory().get('/')) is response


def test_cors_preflight(client, settings):
    settings.CORS_ALLOWED_ORIGINS = ['http://localhost:3000']
    response = client.options('/api/users/total', HTTP_ORIGIN='http://localhost:3000',
                              HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
                              HTTP_ACCESS_CONTROL_REQUEST_HEADERS='authorization')
    assert response.status_code == 200
    assert response['Access-Control-Allow-Origin'] == 'http://localhost:3000'
    assert 'authorization' in response['Access-Control-Allow-Headers'].lower()


@pytest.mark.parametrize('path', PROTECTED[:4])
@pytest.mark.parametrize('user', [
    {'id': 9, 'role': 'User'}, {'id': 9}, {'role': 'admin'}, None, 'Admin',
])
def test_non_admin_cannot_read_statistics(client, token_factory, path, user):
    response = client.get(path, HTTP_AUTHORIZATION=token_factory(user=user))
    assert response.status_code == (401 if user is None else 403)
    assert response.json() == {'error': 'Unauthorized' if user is None else 'Forbidden'}


@pytest.mark.django_db
@pytest.mark.parametrize('path', PROTECTED[:4])
def test_admin_can_read_statistics(authorized_client, path):
    assert authorized_client.get(path).status_code == 200
