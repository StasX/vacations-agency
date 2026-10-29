import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def config_env(monkeypatch):
    for name in ('DJANGO_DEBUG', 'DJANGO_ALLOWED_HOSTS', 'DJANGO_CORS_ALLOWED_ORIGINS', 'DJANGO_COOKIE_SECURE'):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def load_config(module='api.settings'):
    # A fresh process avoids settings-module caching between profile checks.
    code = (
        'import importlib,json; c=importlib.import_module(' + repr(module) + '); '
        'print(json.dumps({k:getattr(c,k) for k in '
        '["DEBUG","ALLOWED_HOSTS","CORS_ALLOW_ALL_ORIGINS","CORS_ALLOWED_ORIGINS",'
        '"SESSION_COOKIE_SECURE","AUTH_COOKIE_SECURE","CSRF_COOKIE_SECURE"]}))'
    )
    environment = dict(os.environ, PYTHON_DOTENV_DISABLED='1')
    environment['PYTHONPATH'] = str(Path(__file__).resolve().parents[1] / 'src')
    return json.loads(subprocess.check_output([sys.executable, '-c', code], env=environment, text=True))


def test_secure_defaults(config_env):
    config = load_config()
    assert config['DEBUG'] is False
    assert config['ALLOWED_HOSTS'] == ['localhost', '127.0.0.1', '[::1]']
    assert config['CORS_ALLOW_ALL_ORIGINS'] is False
    assert config['CORS_ALLOWED_ORIGINS'] == []
    assert config['SESSION_COOKIE_SECURE'] is True
    assert config['AUTH_COOKIE_SECURE'] is True
    assert config['CSRF_COOKIE_SECURE'] is True


def test_environment_configuration(config_env):
    config_env.setenv('DJANGO_DEBUG', ' True ')
    config_env.setenv('DJANGO_ALLOWED_HOSTS', ' agency.example.com, api.example.com, ')
    config_env.setenv('DJANGO_CORS_ALLOWED_ORIGINS', ' https://agency.example.com, ')
    config = load_config('api.settings.development')
    assert config['DEBUG'] is True
    assert config['ALLOWED_HOSTS'] == ['agency.example.com', 'api.example.com']
    assert config['CORS_ALLOWED_ORIGINS'] == ['https://agency.example.com']


def test_production_ignores_development_security_switches(config_env):
    config_env.setenv('DJANGO_DEBUG', 'true')
    config_env.setenv('DJANGO_COOKIE_SECURE', 'false')
    config = load_config('api.settings.production')
    assert config['DEBUG'] is False
    assert all(config[key] for key in ('SESSION_COOKIE_SECURE', 'AUTH_COOKIE_SECURE', 'CSRF_COOKIE_SECURE'))


def test_development_supports_local_http(config_env):
    config = load_config('api.settings.development')
    assert config['DEBUG'] is True
    assert not any(config[key] for key in ('SESSION_COOKIE_SECURE', 'AUTH_COOKIE_SECURE', 'CSRF_COOKIE_SECURE'))


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
