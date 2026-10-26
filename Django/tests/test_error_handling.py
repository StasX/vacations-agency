from types import ModuleType

import pytest
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import path


def install_view(settings, view):
    routes = ModuleType('error_test_routes')
    routes.urlpatterns = [path('', view)]
    settings.ROOT_URLCONF = routes


def test_uncaught_view_error_is_generic_and_logged(client, settings, caplog):
    def fail(request):
        raise RuntimeError('private backend failure')

    install_view(settings, fail)
    response = client.get('/?secret=do-not-log', HTTP_AUTHORIZATION='private-token')
    assert response.status_code == 500
    assert response.json() == {'error': 'Internal server error'}
    assert 'private backend failure' in caplog.text
    assert any(record.exc_info and record.exc_info[2] for record in caplog.records)
    assert 'do-not-log' not in caplog.text
    assert 'private-token' not in caplog.text


@pytest.mark.parametrize('exception,status', [(Http404, 404), (PermissionDenied, 403)])
def test_expected_http_errors_keep_status(client, settings, exception, status):
    def fail(request):
        raise exception()

    install_view(settings, fail)
    assert client.get('/').status_code == status
