from datetime import date
from io import BytesIO
from unittest.mock import MagicMock

import pytest


def form(**changes):
    values = dict(country="1", description="Holiday", start_date="2099-01-01",
                  end_date="2099-01-02", price="100")
    values.update(changes)
    return values


def test_login_root_accepts_post(client, app):
    app.test_dal.get_scalar.return_value = dict(
        id=7, first_name="Test", last_name="User", role=2, password="hash")
    response = client.post(
        "/", data={"email": "test@example.com", "password": "Abc123"})
    assert response.status_code == 302 and response.location == "/vacations"


def test_registration_validation_does_not_touch_database(client, app):
    response = client.post("/register", data={"first_name": "A"})
    assert b"Missing last name." in response.data
    app.test_dal.get_scalar.assert_not_called()
    app.test_dal.insert.assert_not_called()


@pytest.mark.parametrize("role", [1, 2])
def test_empty_vacation_list(client, app, sign_in, role):
    sign_in(role)
    app.test_dal.get_table.return_value = []
    response = client.get("/vacations")
    assert response.status_code == 200
    assert b"delete-btn" not in response.data


@pytest.mark.parametrize("role", [1, 2])
def test_vacation_description_is_html_escaped(client, app, sign_in, role):
    sign_in(role)
    app.test_dal.get_table.return_value = [dict(
        id=1, name="Italy", description='<script>alert("xss")</script>', image=None,
        start_date=date(2099, 1, 1), end_date=date(2099, 1, 2), price=100, likes_count=0, liked=0,
    )]
    response = client.get("/vacations")
    assert response.status_code == 200
    assert b'<script>alert("xss")</script>' not in response.data
    assert b"&lt;script&gt;" in response.data


@pytest.mark.parametrize("method,path", [
    ("post", "/vacations/add"), ("post", "/vacations/1/edit"),
    ("get", "/vacations/images/photo.jpg"),
])
def test_anonymous_requests_do_not_query_or_mutate(client, app, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 302 and response.location == "/login"
    app.test_dal.get_table.assert_not_called()
    app.test_dal.get_scalar.assert_not_called()
    app.test_dal.insert.assert_not_called()
    app.test_dal.update.assert_not_called()
    app.test_dal.delete.assert_not_called()


def test_admin_add_form_renders_countries(client, app, sign_in):
    sign_in(1)
    app.test_dal.get_table.return_value = [{"id": 1, "name": "Italy"}]
    response = client.get("/vacations/add")
    assert response.status_code == 200
    assert b"Italy" in response.data and b"Add Vacation" in response.data


@pytest.mark.parametrize("data,message", [
    (form(description=""), b"Missing description."),
    (form(), b"Missing image."),
])
def test_invalid_add_renders_error_without_mutation(client, app, sign_in, data, message):
    sign_in(1)
    app.test_dal.get_table.return_value = [{"id": 1, "name": "Italy"}]
    response = client.post("/vacations/add", data=data)
    assert response.status_code == 200
    assert message in response.data
    app.test_dal.insert.assert_not_called()


def test_admin_edit_form_renders_existing_values(client, app, sign_in):
    sign_in(1)
    app.test_dal.get_scalar.return_value = dict(
        id=12, country="Italy", country_id=1, description="Existing holiday", image=None,
        start_date=date(2099, 1, 1), end_date=date(2099, 1, 2), price=100,
    )
    app.test_dal.get_table.return_value = [{"id": 1, "name": "Italy"}]
    response = client.get("/vacations/12/edit")
    assert response.status_code == 200
    for text in (b"Existing holiday", b"Italy", b"2099-01-01", b"100"):
        assert text in response.data
    assert app.test_dal.get_scalar.call_args.args[1] == (12,)


@pytest.mark.parametrize("replace", [False, True])
def test_admin_edit_keeps_or_replaces_image(client, app, sign_in, image_directory, replace):
    sign_in(1)
    old = image_directory / "old.jpg"
    old.write_bytes(b"old")
    app.test_dal.get_scalar.return_value = {"image": old.name}
    data = form(image=(BytesIO(b"new" if replace else b""),
                "new.jpg" if replace else ""))
    response = client.post("/vacations/12/edit", data=data)
    assert response.status_code == 302 and response.location == "/vacations"
    params = app.test_dal.update.call_args.args[1]
    assert params[:5] == ("1", "Holiday", "2099-01-01", "2099-01-02", "100")
    assert params[-1] == 12
    assert old.exists() == (not replace)
    assert (image_directory /
            params[-2]).read_bytes() == (b"new" if replace else b"old")


@pytest.mark.parametrize("signed_in", [False, True])
@pytest.mark.parametrize("exists", [False, True])
def test_image_route_access_and_fallback(client, sign_in, image_directory, signed_in, exists):
    if signed_in:
        sign_in()
    if exists:
        (image_directory / "photo.jpg").write_bytes(b"photo")
    response = client.get("/vacations/images/photo.jpg")
    if not signed_in:
        assert response.status_code == 302 and response.location == "/login"
    else:
        assert response.status_code == 200
        assert response.data == (b"photo" if exists else b"fallback")
    response.close()


def test_exception_handler_logs_and_renders_generic_error(client, app, sign_in, monkeypatch):
    sign_in()
    error = RuntimeError("private database details")
    app.test_dal.get_table.side_effect = error
    logger = MagicMock()
    monkeypatch.setattr("app.Logger.write_log", logger)
    response = client.get("/vacations")
    logger.assert_called_once_with(error)
    assert b"private database details" not in response.data
    assert b"Reload" in response.data


@pytest.mark.xfail(strict=True, reason="Exception handler currently returns HTTP 200")
def test_unexpected_exception_returns_500(client, app, sign_in, monkeypatch):
    sign_in()
    app.test_dal.get_table.side_effect = RuntimeError("offline")
    monkeypatch.setattr("app.Logger.write_log", lambda error: None)
    assert client.get("/vacations").status_code == 500


@pytest.mark.xfail(strict=True, reason="Likes route does not handle anonymous AuthError")
def test_anonymous_like_redirects_without_mutation(client, app, monkeypatch):
    monkeypatch.setattr("app.Logger.write_log", lambda error: None)
    response = client.post("/likes/like/12")
    app.test_dal.insert.assert_not_called()
    app.test_dal.delete.assert_not_called()
    assert response.status_code == 302 and response.location == "/login"


@pytest.mark.parametrize("path", ["/vacations/999/edit", "/vacations/999/delete"])
@pytest.mark.xfail(strict=True, reason="Missing vacations do not produce a 404 response")
def test_missing_vacation_returns_404(client, app, sign_in, monkeypatch, path):
    sign_in(1)
    app.test_dal.get_scalar.return_value = None
    app.test_dal.get_table.return_value = []
    monkeypatch.setattr("app.Logger.write_log", lambda error: None)
    response = client.post(path) if path.endswith('/delete') else client.get(path)
    assert response.status_code == 404


@pytest.mark.xfail(strict=True, reason="Missing multipart image field becomes a generic error during edit")
def test_edit_without_image_field_preserves_image(client, app, sign_in, monkeypatch):
    sign_in(1)
    app.test_dal.get_scalar.return_value = {"image": "old.jpg"}
    monkeypatch.setattr("app.Logger.write_log", lambda error: None)
    assert client.post("/vacations/12/edit", data=form()).status_code == 302
    assert app.test_dal.update.call_args.args[1][-2] == "old.jpg"


def test_delete_get_does_not_mutate(client, app, sign_in, monkeypatch):
    sign_in(1)
    app.test_dal.get_scalar.return_value = {"image": None}
    monkeypatch.setattr("app.Logger.write_log", lambda error: None)
    assert client.get("/vacations/12/delete").status_code == 405
    app.test_dal.delete.assert_not_called()


def test_add_without_csrf_token_is_rejected(client, app, sign_in, image_directory):
    app.config["CSRF_ENABLED"] = True
    sign_in(1)
    response = client.post(
        "/vacations/add", data=form(image=(BytesIO(b"image"), "image.jpg")))
    assert response.status_code in (400, 403)
    app.test_dal.insert.assert_not_called()


@pytest.mark.xfail(strict=True, reason="Uploaded files are not validated on the server")
def test_non_image_upload_is_rejected(client, app, sign_in, image_directory):
    sign_in(1)
    app.test_dal.get_table.return_value = []
    client.post("/vacations/add",
                data=form(image=(BytesIO(b"<script>alert(1)</script>"), "attack.html")))
    app.test_dal.insert.assert_not_called()
    assert not list(image_directory.iterdir())
