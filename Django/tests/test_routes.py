import pytest
from django.urls import resolve


@pytest.mark.parametrize('method', ['get', 'head'])
def test_health_probe(client, monkeypatch, method):
    def unavailable(*args, **kwargs):
        pytest.fail('Health probe must not access Redis')
    monkeypatch.setattr('utils.refresh_tokens.get_redis', unavailable)
    response = getattr(client, method)('/health')
    assert response.status_code == 200
    assert response.content == b''
    assert 'Location' not in response
    assert not response.cookies


def test_health_check(client):
    response = client.get('/')
    assert response.status_code == 200
    assert response.json() == {'status': 'OK'}
    assert response['Content-Type'] == 'application/json'


@pytest.mark.parametrize('method', ['post', 'put', 'delete', 'patch'])
def test_health_check_methods(client, method):
    assert getattr(client, method)('/').status_code == 405


@pytest.mark.parametrize('path,name', [
    ('/api/auth/login', 'login'), ('/api/auth/logout', 'logout'),
    ('/api/auth/refresh-token', 'refresh_token'),
    ('/api/users/total', 'total_users'), ('/api/likes/total', 'total_likes'),
    ('/api/likes/statistics', 'likes_statistics'),
    ('/api/vacations/statistics', 'vacations_statistics'),
])
def test_url_mapping(path, name):
    view = resolve(path).func
    assert getattr(view, 'cls', view).__name__ == name


def test_unknown_api_route(authorized_client):
    response = authorized_client.get('/api/does-not-exist')
    assert response.status_code == 404
    assert response.json() == {'error': 'Not Found'}


def test_unknown_non_api_route_returns_not_found(authorized_client):
    response = authorized_client.get('/does-not-exist')
    assert response.status_code == 404
    assert response.json() == {'error': 'Not Found'}


@pytest.mark.parametrize('path', ['/api/does-not-exist', '/does-not-exist', '/api/auth/login/'])
@pytest.mark.parametrize('authorization', ['', 'invalid-token'])
def test_unknown_routes_do_not_require_authentication(client, path, authorization):
    response = client.get(path, HTTP_AUTHORIZATION=authorization)
    assert response.status_code == 404
    assert response.json() == {'error': 'Not Found'}
