from datetime import date
from io import BytesIO

import pytest


@pytest.mark.parametrize("path", ["/", "/login", "/register"])
def test_public_pages(client, path):
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/vacations", "/vacations/add", "/vacations/1/edit", "/vacations/1/delete"])
def test_anonymous_users_are_redirected(client, app, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.location == "/login"
    app.test_dal.delete.assert_not_called()


@pytest.mark.parametrize("method,path", [
    ("get", "/vacations/add"), ("post", "/vacations/add"),
    ("get", "/vacations/1/edit"), ("post", "/vacations/1/edit"),
    ("get", "/vacations/1/delete"),
])
def test_regular_users_cannot_manage_vacations(client, app, sign_in, path, method):
    sign_in()
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert response.location == "/login"
    app.test_dal.insert.assert_not_called()
    app.test_dal.update.assert_not_called()
    app.test_dal.delete.assert_not_called()


@pytest.mark.parametrize("role", [1, 2])
def test_vacation_list_formats_dates_and_uses_current_user(client, app, sign_in, role):
    sign_in(role)
    app.test_dal.get_table.return_value = [dict(
        id=1, name="Italy", description="Rome holiday", start_date=date(2099, 1, 1),
        end_date=date(2099, 1, 2), price=100, image=None, likes_count=3, liked=1,
    )]
    response = client.get("/vacations")
    assert response.status_code == 200
    assert b"Rome holiday" in response.data
    assert b"01/01/2099" in response.data
    assert app.test_dal.get_table.call_args.args[1] == (7,)
    assert (b"delete-btn" in response.data) == (role == 1)


@pytest.mark.parametrize("already_liked", [False, True])
def test_like_toggles_for_current_user(client, app, sign_in, already_liked):
    sign_in()
    app.test_dal.get_scalar.return_value = {"cnt": int(already_liked)}
    response = client.get("/likes/like/12")
    assert response.status_code == 302
    operation = app.test_dal.delete if already_liked else app.test_dal.insert
    assert operation.call_args.args[1] == (7, 12)


def test_admin_add_saves_uploaded_image(client, app, sign_in, tmp_path, monkeypatch):
    sign_in(1)
    monkeypatch.setattr(app, "root_path", str(tmp_path))
    image_dir = tmp_path / "static/images/vacations"
    image_dir.mkdir(parents=True)
    response = client.post("/vacations/add", data=dict(
        country="1", description="Rome holiday", start_date="2099-01-01",
        end_date="2099-01-02", price="100", image=(BytesIO(b"test image"), "rome.jpg"),
    ))
    assert response.status_code == 302
    params = app.test_dal.insert.call_args.args[1]
    assert params[:3] == ("1", "Rome holiday", "2099-01-01")
    assert (image_dir / params[-1]).read_bytes() == b"test image"


def test_admin_delete_removes_record_and_image(client, app, sign_in, tmp_path, monkeypatch):
    sign_in(1)
    monkeypatch.setattr(app, "root_path", str(tmp_path))
    image = tmp_path / "static/images/vacations/rome.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    app.test_dal.get_scalar.return_value = {"image": "rome.jpg"}
    assert client.get("/vacations/1/delete").status_code == 302
    assert not image.exists()
    assert app.test_dal.delete.call_args.args[1] == (1,)


@pytest.mark.xfail(strict=True, reason="404 handler currently returns HTTP 200")
def test_missing_page_returns_404(client):
    assert client.get("/missing-page").status_code == 404


@pytest.mark.xfail(strict=True, reason="Edit error handler uses incorrect country column names")
def test_invalid_edit_shows_validation_message(client, app, sign_in, monkeypatch):
    sign_in(1)
    monkeypatch.setattr("app.Logger.write_log", lambda error: None)
    app.test_dal.get_table.return_value = [{"id": 1, "name": "Italy"}]
    app.test_dal.get_scalar.return_value = {"image": None}
    response = client.post("/vacations/1/edit", data=dict(
        country="1", description="", start_date="2099-01-01", end_date="2099-01-02",
        price="100", image=(BytesIO(b""), ""),
    ))
    assert b"Missing description." in response.data
