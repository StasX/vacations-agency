import pytest
from flask import session
from facades.auth_facade import AuthFacade
from facades.likes_facade import LikesFacade
from facades.vacations_facade import VacationsFacade
from models.client_errors import AuthError, ValidationError


@pytest.mark.parametrize("role,method,allowed", [
    (None, "block_anonymous", False), (None, "block_non_admin", False),
    (2, "block_anonymous", True), (2, "block_non_admin", False),
    (1, "block_anonymous", True), (1, "block_non_admin", True),
])
def test_auth_guards(app, role, method, allowed):
    with app.test_request_context():
        if role:
            session["current_user"] = {"id": 7, "role": role}
        if allowed:
            assert getattr(AuthFacade(), method)() is None
        else:
            with pytest.raises(AuthError):
                getattr(AuthFacade(), method)()


def test_anonymous_like_raises_before_database_query(app):
    with app.test_request_context(), pytest.raises(AuthError):
        LikesFacade().like(12)
    app.test_dal.get_scalar.assert_not_called()
    app.test_dal.insert.assert_not_called()


def test_validation_error_contains_submitted_model(app):
    with app.test_request_context(method="POST", data={"email": "bad", "password": "x"}):
        with pytest.raises(ValidationError) as caught:
            AuthFacade().login()
    assert caught.value.model.email == "bad"
    assert caught.value.model.password == "x"


def test_vacation_error_preserves_form_data(app):
    with app.test_request_context(method="POST", data={"country": "1", "description": ""}):
        with pytest.raises(ValidationError) as caught:
            VacationsFacade().add_vacation()
    assert caught.value.model.country == "1"
    assert caught.value.message == "Missing description."
    app.test_dal.insert.assert_not_called()


@pytest.mark.parametrize("raises", [False, True])
def test_vacation_context_manager_closes_on_success_and_failure(app, raises):
    if raises:
        with pytest.raises(RuntimeError):
            with VacationsFacade():
                raise RuntimeError("failure")
    else:
        facade = VacationsFacade()
        with facade as entered:
            assert entered is facade
    app.test_dal.close.assert_called_once_with()


def test_get_old_image(app):
    app.test_dal.get_scalar.return_value = {"image": "old.jpg"}
    assert VacationsFacade().get_old_image(12) == "old.jpg"
    assert app.test_dal.get_scalar.call_args.args[1] == (12,)


def test_authenticated_request_closes_database_connections(client, request_connections, sign_in):
    sign_in()
    assert client.get("/vacations").status_code == 200
    assert request_connections
    for connection in request_connections:
        connection.close.assert_called_once_with()
