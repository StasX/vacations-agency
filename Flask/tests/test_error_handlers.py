from unittest.mock import Mock

import pytest
from werkzeug.exceptions import BadRequest, Forbidden, MethodNotAllowed, Unauthorized, RequestEntityTooLarge, TooManyRequests


@pytest.mark.parametrize("error", [BadRequest(), Unauthorized(), Forbidden(),
                                        MethodNotAllowed(valid_methods=["POST"]),
                                        RequestEntityTooLarge(), TooManyRequests(retry_after=60)])
def test_http_errors_preserve_status_and_headers(app, monkeypatch, error):
    logger = Mock()
    monkeypatch.setattr("app.Logger.write_log", logger)
    with app.test_request_context():
        response = app.make_response(app.handle_user_exception(error))
    assert response.status_code == error.code
    if error.code == 405:
        assert response.headers["Allow"] == "POST"
    if error.code == 429:
        assert response.headers["Retry-After"] == "60"
    assert response.mimetype == "text/html"
    assert b'class="error-page"' in response.data
    if error.code != 405:
        assert error.name.encode() in response.data
    logger.assert_not_called()


def test_missing_page_renders_custom_template(client):
    response = client.get("/missing-page")
    assert response.status_code == 404
    assert response.mimetype == "text/html"
    assert b"<!DOCTYPE html>" in response.data


@pytest.mark.parametrize("path", ["/logout", "/vacations/12/delete", "/likes/like/12"])
def test_method_not_allowed_renders_custom_template(client, path):
    response = client.get(path)
    assert response.status_code == 405
    assert response.mimetype == "text/html"
    assert "POST" in response.headers["Allow"]
    assert b"This action is not allowed." in response.data
    assert b'href="/login"' in response.data


def test_http_error_description_is_escaped(app):
    with app.test_request_context():
        error = BadRequest(description='<script>alert("xss")</script>')
        response = app.make_response(app.handle_user_exception(error))
    assert response.status_code == 400
    assert b"<script>alert" not in response.data
    assert b"&lt;script&gt;" in response.data


def test_csrf_failure_renders_error_page(client, app):
    app.config["CSRF_ENABLED"] = True
    response = client.post("/login")
    assert response.status_code == 400
    assert b'class="error-page"' in response.data
    assert b"Invalid or missing CSRF token" in response.data


@pytest.mark.parametrize("signed_in", [False, True])
@pytest.mark.parametrize("path,method,status", [
    ("/missing-page", "get", 404),
    ("/logout", "get", 405),
    ("/login", "post", 400),
])
def test_error_navigation_uses_session(client, app, sign_in, signed_in, path, method, status):
    app.config["CSRF_ENABLED"] = True
    if signed_in:
        sign_in()
    response = getattr(client, method)(path)
    assert response.status_code == status
    target = b'/vacations' if signed_in else b'/login'
    assert b'href="' + target + b'"' in response.data
    assert b"history.back()" not in response.data


@pytest.mark.parametrize("signed_in", [False, True])
def test_server_error_navigation_uses_session(client, app, sign_in, monkeypatch, signed_in):
    if signed_in:
        sign_in()
    def fail():
        raise RuntimeError("private error")
    monkeypatch.setitem(app.view_functions, "auth_view.login", fail)
    monkeypatch.setattr("app.Logger.write_log", lambda error: None)
    response = client.get("/login")
    assert response.status_code == 500
    target = b'/vacations' if signed_in else b'/login'
    assert b'href="' + target + b'"' in response.data
    assert b"history." not in response.data
    assert b"private error" not in response.data
