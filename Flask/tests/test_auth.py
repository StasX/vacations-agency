import pytest

from utils.security import Security


def test_login_stores_user_without_password(client, app):
    app.test_dal.get_scalar.return_value = dict(
        id=7, first_name="Test", last_name="User", email="test@example.com",
        password=Security.hash("Abc123"), role=2,
    )
    response = client.post(
        "/login", data={"email": "test@example.com", "password": "Abc123"})
    assert response.status_code == 302
    assert response.location == "/vacations"
    with client.session_transaction() as session:
        assert session["current_user"]["id"] == 7
        assert "password" not in session["current_user"]
    params = app.test_dal.get_scalar.call_args.args[1]
    assert params == ("test@example.com",)


def test_wrong_password_does_not_create_session(client, app):
    app.test_dal.get_scalar.return_value = None
    response = client.post(
        "/login", data={"email": "test@example.com", "password": "wrong"})
    assert b"Invalid Email or Password." in response.data
    with client.session_transaction() as session:
        assert "current_user" not in session


def test_invalid_login_does_not_query_database(client, app):
    response = client.post("/login", data={"email": "bad", "password": "x"})
    assert b"Invalid Email or Password." in response.data
    app.test_dal.get_scalar.assert_not_called()


def test_duplicate_registration_does_not_insert(client, app):
    app.test_dal.get_scalar.return_value = {"COUNT(*)": 1}
    response = client.post("/register", data=dict(
        first_name="Test", last_name="User", email="test@example.com", password="Abc123"
    ))
    assert b"Email already exists." in response.data
    app.test_dal.insert.assert_not_called()


@pytest.mark.parametrize("field,value,message", [
    ("first_name", "x" * 16, b"First name length should be 2-15 characters."),
    ("last_name", "x" * 16, b"Last name length should be 2-15 characters."),
    ("email", "a" * 26 + "@b.co", b"Email length must be 6 to 30 characters."),
    ("password", "x" * 33, b"Password length must be 4 to 32 characters."),
])
def test_registration_rejects_overlong_fields_before_database_write(client, app, field, value, message):
    data = dict(first_name="Test", last_name="User", email="test@example.com", password="Abc123")
    data[field] = value
    response = client.post("/register", data=data)
    assert response.status_code == 200
    assert message in response.data
    app.test_dal.get_scalar.assert_not_called()
    app.test_dal.insert.assert_not_called()
    with client.session_transaction() as session:
        assert "current_user" not in session


def test_registration_forces_user_role_and_hashes_password(client, app):
    app.test_dal.get_scalar.side_effect = [
        {"COUNT(*)": 0},
        dict(id=8, first_name="Test", last_name="User",
             email="test@example.com", password="hash", role=2),
    ]
    response = client.post("/register", data=dict(
        first_name="Test", last_name="User", email="test@example.com", password="Abc123", role=1
    ))
    assert response.status_code == 302
    params = app.test_dal.insert.call_args.args[1]
    assert params[-1] == 2
    assert Security.verify("Abc123", params[-2])
    with client.session_transaction() as session:
        assert session["current_user"]["id"] == 8
        assert "password" not in session["current_user"]


def test_logout_clears_session(client, sign_in):
    sign_in()
    assert client.post("/logout").status_code == 302
    with client.session_transaction() as session:
        assert not session


def test_login_discards_previous_session_data(client, app):
    with client.session_transaction() as session:
        session["_csrf_token"] = "old-token"
        session["stale"] = True
    app.test_dal.get_scalar.return_value = dict(
        id=7, first_name="Test", last_name="User", password=Security.hash("Abc123"), role=2)
    assert client.post("/login", data={"email": "test@example.com", "password": "Abc123"}).status_code == 302
    with client.session_transaction() as session:
        assert session["current_user"]["id"] == 7
        assert "_csrf_token" not in session
        assert "stale" not in session
