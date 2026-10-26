import runpy
from importlib.util import find_spec

import pytest


@pytest.fixture
def config_env(monkeypatch):
    for name in ('DJANGO_DEBUG', 'DJANGO_ALLOWED_HOSTS', 'DJANGO_CORS_ALLOWED_ORIGINS'):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_secure_defaults(config_env):
    config = runpy.run_path(find_spec('api.settings').origin)
    assert config['DEBUG'] is False
    assert config['ALLOWED_HOSTS'] == ['localhost', '127.0.0.1', '[::1]']
    assert config['CORS_ALLOW_ALL_ORIGINS'] is False
    assert config['CORS_ALLOWED_ORIGINS'] == []


def test_environment_configuration(config_env):
    config_env.setenv('DJANGO_DEBUG', ' True ')
    config_env.setenv('DJANGO_ALLOWED_HOSTS', ' agency.example.com, api.example.com, ')
    config_env.setenv('DJANGO_CORS_ALLOWED_ORIGINS', ' https://agency.example.com, ')
    config = runpy.run_path(find_spec('api.settings').origin)
    assert config['DEBUG'] is True
    assert config['ALLOWED_HOSTS'] == ['agency.example.com', 'api.example.com']
    assert config['CORS_ALLOWED_ORIGINS'] == ['https://agency.example.com']


def test_unknown_host_rejected(client):
    assert client.get('/', HTTP_HOST='untrusted.example').status_code == 400


@pytest.mark.parametrize('origin,allowed', [
    ('https://agency.example.com', True),
    ('https://untrusted.example', False),
])
def test_credentialed_cors_allowlist(client, settings, origin, allowed):
    settings.CORS_ALLOWED_ORIGINS = ['https://agency.example.com']
    response = client.options('/api/auth/login', HTTP_ORIGIN=origin,
                              HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
                              HTTP_ACCESS_CONTROL_REQUEST_HEADERS='content-type')
    assert response.status_code == 200
    if allowed:
        assert response['Access-Control-Allow-Origin'] == origin
        assert response['Access-Control-Allow-Credentials'] == 'true'
    else:
        assert 'Access-Control-Allow-Origin' not in response


def test_cors_disabled_by_default(client):
    response = client.options('/api/auth/login', HTTP_ORIGIN='http://localhost:5173',
                              HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST')
    assert 'Access-Control-Allow-Origin' not in response
