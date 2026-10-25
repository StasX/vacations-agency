import re
from datetime import date
from io import BytesIO
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def enable_csrf(app):
    app.config["CSRF_ENABLED"] = True


@pytest.mark.parametrize("path", ["/", "/login", "/register", "/vacations/add", "/vacations/12/edit", "/vacations/12/delete", "/likes/like/12"])
@pytest.mark.parametrize("token", [None, "forged", "\u2603"])
def test_invalid_tokens_block_submissions(client, app, path, token):
    client.get("/login")
    response = client.post(path, data={} if token is None else {"csrf_token": token})
    assert response.status_code == 400
    app.test_dal.insert.assert_not_called()
    app.test_dal.update.assert_not_called()
    app.test_dal.delete.assert_not_called()


@pytest.mark.parametrize("path,target", [
    ("/login", "views.auth_view.AuthFacade.login"),
    ("/", "views.auth_view.AuthFacade.login"),
    ("/register", "views.auth_view.AuthFacade.register"),
    ("/vacations/add", "views.vacations_view.VacationsFacade.add_vacation"),
    ("/vacations/12/edit", "views.vacations_view.VacationsFacade.update_vacation"),
])
def test_form_tokens_allow_submission(client, app, sign_in, path, target):
    sign_in(1)
    app.test_dal.get_table.return_value = [{"id": 1, "name": "Italy"}]
    app.test_dal.get_scalar.return_value = dict(
        id=12, country="Italy", country_id=1, description="Holiday", image=None,
        start_date=date(2099, 1, 1), end_date=date(2099, 1, 2), price=100,
    )
    page = client.get(path)
    assert page.status_code == 200
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
    with patch(target) as submit:
        response = client.post(path, data={"csrf_token": token, "image": (BytesIO(b"image"), "trip.jpg")})
    assert response.status_code == 302
    submit.assert_called_once()


def test_token_from_another_session_is_rejected(client, app):
    client.get("/login")
    with client.session_transaction() as session:
        token = session["_csrf_token"]
    other = app.test_client()
    other.get("/login")
    assert other.post("/login", data={"csrf_token": token}).status_code == 400


def test_token_without_session_is_rejected(client):
    assert client.post("/login", data={"csrf_token": "forged"}).status_code == 400


def test_admin_delete_form_submits_with_csrf(client, app, sign_in, image_directory):
    sign_in(1)
    image = image_directory / "trip.jpg"
    image.write_bytes(b"image")
    app.test_dal.get_table.return_value = [dict(
        id=12, name="Italy", description="Holiday", image="trip.jpg", price=100,
        start_date=date(2099, 1, 1), end_date=date(2099, 1, 2), likes_count=0, liked=0,
    )]
    app.test_dal.get_scalar.return_value = {"image": "trip.jpg"}
    page = client.get("/vacations")
    assert b'method="post" action="/vacations/12/delete"' in page.data
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
    assert client.post("/vacations/12/delete", data={"csrf_token": token}).status_code == 302
    app.test_dal.delete.assert_called_once()
    assert app.test_dal.delete.call_args.args[1] == (12,)
    assert not image.exists()


@pytest.mark.parametrize("liked", [0, 1])
def test_user_like_form_requires_post_and_csrf(client, app, sign_in, liked):
    sign_in()
    app.test_dal.get_table.return_value = [dict(
        id=12, name="Italy", description="Holiday", image=None, price=100,
        start_date=date(2099, 1, 1), end_date=date(2099, 1, 2), likes_count=liked, liked=liked,
    )]
    app.test_dal.get_scalar.return_value = {"cnt": liked}
    page = client.get("/vacations")
    assert b'method="post" action="/likes/like/12"' in page.data
    token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
    assert client.get("/likes/like/12").status_code == 405
    app.test_dal.insert.assert_not_called()
    app.test_dal.delete.assert_not_called()
    assert client.post("/likes/like/12", data={"csrf_token": token}).status_code == 302
    operation = app.test_dal.delete if liked else app.test_dal.insert
    operation.assert_called_once()
    assert operation.call_args.args[1] == (7, 12)
