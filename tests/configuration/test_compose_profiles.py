"""Inspect resolved Compose profiles without starting Docker or loading real secrets."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def clean_environment():
    environment = dict(os.environ)
    for template in ('development.env.example', 'production.env.example'):
        for line in (ROOT / 'config' / template).read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                environment.pop(line.split('=', 1)[0], None)
    for key in ('COMPOSE_PROJECT_NAME', 'COMPOSE_FILE', 'COMPOSE_PROFILES'):
        environment.pop(key, None)
    return environment


def compose(*files):
    if not shutil.which('docker'):
        pytest.skip('Docker Compose CLI is required; no daemon is needed')
    command = ['docker', 'compose', '--env-file', 'config/development.env.example']
    for file in files:
        command.extend(['-f', file])
    command.extend(['config', '--format', 'json'])
    return json.loads(subprocess.check_output(command, cwd=ROOT, text=True, env=clean_environment()))


def test_base_is_production_even_with_development_environment_file():
    config = compose('docker-compose.yml')
    services = config['services']
    django = services['vacations-statistics']
    flask = services['vacations-catalog']
    frontend = services['vacations-statistics-frontend']
    assert django['environment']['DJANGO_SETTINGS_MODULE'] == 'api.settings.production'
    assert django['environment']['DJANGO_DEBUG'] == 'false'
    assert django['environment']['DJANGO_COOKIE_SECURE'] == 'true'
    assert flask['environment']['APP_ENV'] == 'production'
    assert flask['environment']['FLASK_COOKIE_SECURE'] == 'true'
    assert not django.get('ports')
    assert not services['vacations-database'].get('ports')
    assert not services['vacations-redis'].get('ports')
    for service in (django, flask, frontend):
        assert not any(volume['type'] == 'bind' for volume in service.get('volumes', []))
        assert all(port['host_ip'] == '127.0.0.1' for port in service.get('ports', []))
        assert service.get('entrypoint') is None
    assert frontend['build']['dockerfile'] == 'Dockerfile'
    initializer = services['account-initialization']
    assert Path(initializer['build']['context']) == ROOT / 'scripts' / 'account-status'
    assert 'DJANGO_SETTINGS_MODULE' not in initializer['environment']
    assert 'SECRET_KEY' not in initializer['environment']
    assert not initializer.get('volumes')
    assert initializer['depends_on']['vacations-database']['condition'] == 'service_healthy'
    assert initializer['depends_on']['vacations-redis']['condition'] == 'service_healthy'
    for backend in (django, flask):
        assert backend['depends_on']['account-initialization']['condition'] == 'service_completed_successfully'
    for name in ('vacations-redis', 'vacations-database', 'vacations-statistics',
                 'vacations-catalog', 'vacations-statistics-frontend'):
        assert services[name]['container_name'] == name


def test_production_template_requires_credentials_before_startup():
    if not shutil.which('docker'):
        pytest.skip('Docker Compose CLI is required')
    result = subprocess.run(
        ['docker', 'compose', '--env-file', 'config/production.env.example',
         '-f', 'docker-compose.yml', 'config', '--quiet'],
        cwd=ROOT, text=True, capture_output=True, env=clean_environment())
    assert result.returncode != 0
    assert 'Set ' in result.stderr


def test_development_selects_reload_servers_and_isolated_volumes():
    config = compose('docker-compose.yml', 'compose.development.yml')
    production = compose('docker-compose.yml')
    services = config['services']
    django = services['vacations-statistics']
    flask = services['vacations-catalog']
    frontend = services['vacations-statistics-frontend']
    assert config['name'] == 'vacations-development'
    assert django['environment']['DJANGO_SETTINGS_MODULE'] == 'api.settings.development'
    assert django['environment']['DJANGO_COOKIE_SECURE'] == 'false'
    assert flask['environment']['APP_ENV'] == 'development'
    assert flask['environment']['FLASK_COOKIE_SECURE'] == 'false'
    assert 'runserver' in django['entrypoint']
    assert '--debug' in flask['entrypoint']
    assert frontend['build']['dockerfile'] == 'Dockerfile.development'
    assert frontend['environment']['API_PROXY_TARGET'] == 'http://vacations-statistics:8000'
    expected_names = {
        'vacations-redis': 'vacations-development-redis',
        'vacations-database': 'vacations-development-database',
        'vacations-statistics': 'vacations-development-statistics',
        'vacations-catalog': 'vacations-development-catalog',
        'vacations-statistics-frontend': 'vacations-development-statistics-frontend',
    }
    for service, name in expected_names.items():
        assert services[service]['container_name'] == name
        assert name != production['services'][service]['container_name']
    for key in ('vacations-volume', 'redis-volume', 'vacation-images'):
        assert config['volumes'][key]['name'] != production['volumes'][key]['name']
    for service in (django, flask, frontend):
        assert any(volume['type'] == 'bind' for volume in service['volumes'])
        assert all(port['host_ip'] == '127.0.0.1' for port in service.get('ports', []))


def test_test_environments_have_distinct_container_names():
    expected = {
        'compose.mysql-tests.yml': {
            'redis': 'vacations-mysql-tests-redis',
            'mysql': 'vacations-mysql-tests-database',
            'django-tests': 'vacations-mysql-tests-django',
            'flask-tests': 'vacations-mysql-tests-flask',
        },
        'compose.redis-tests.yml': {
            'redis': 'vacations-redis-tests-redis',
            'redis-tests': 'vacations-redis-tests-runner',
        },
        'compose.browser-tests.yml': {
            'mysql': 'vacations-browser-tests-database',
            'redis': 'vacations-browser-tests-redis',
        },
    }
    names = set()
    for files in [('docker-compose.yml',), ('docker-compose.yml', 'compose.development.yml')]:
        names.update(service['container_name'] for service in compose(*files)['services'].values()
                     if service.get('container_name'))
    for file, services in expected.items():
        config = compose(file)
        for service, name in services.items():
            assert config['services'][service]['container_name'] == name
            assert name not in names
            names.add(name)
