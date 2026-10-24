from io import BytesIO
from unittest.mock import Mock

import pytest


@pytest.mark.django_db
def test_wsgi_health_request():
    from api.wsgi import application
    start = Mock()
    environ = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/', 'SERVER_NAME': 'testserver',
               'SERVER_PORT': '80', 'SERVER_PROTOCOL': 'HTTP/1.1',
               'wsgi.url_scheme': 'http', 'wsgi.input': BytesIO(b'')}
    body = b''.join(application(environ, start))
    assert start.call_args.args[0] == '200 OK'
    assert body == b'{"status": "OK"}'


@pytest.mark.parametrize('render_error', [False, True])
def test_wsgi_renders_and_closes_response(monkeypatch, render_error):
    from api import wsgi
    class Response:
        def __init__(self):
            self.render = Mock(side_effect=ValueError('render failed') if render_error else None)
            self.close = Mock()

        def __iter__(self):
            yield b'first'
            yield b'second'

    response = Response()
    monkeypatch.setattr(wsgi, 'django_application', lambda environ, start: response)
    assert list(wsgi.application({}, Mock())) == [b'first', b'second']
    response.render.assert_called_once_with()
    response.close.assert_called_once_with()


def test_wsgi_closes_response_after_iteration_failure(monkeypatch):
    from api import wsgi
    class Response:
        close = Mock()

        def __iter__(self):
            yield b'first'
            raise RuntimeError('stream interrupted')

    response = Response()
    monkeypatch.setattr(wsgi, 'django_application', lambda environ, start: response)
    stream = wsgi.application({}, Mock())
    assert next(stream) == b'first'
    with pytest.raises(RuntimeError, match='stream interrupted'):
        next(stream)
    response.close.assert_called_once_with()


def test_asgi_application_available():
    from api.asgi import application
    assert callable(application)
