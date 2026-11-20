from utils.auth_token import COOKIE
import pytest

from utils.security import Security


def test_login_issues_jwt_without_password(client, app, auth_claims):
    app.test_dal.get_scalar.return_value = dict(
        id=7, first_name="Test", last_name="User", email="test@example.com",
        password=Security.hash("Abc123"), role=2,
    )
    response = client.post(
        "/login", data={"email": "test@example.com", "password": "Abc123"})
    assert response.status_code == 302
    assert response.location == "/vacations"
    claims = auth_claims()
    assert claims["sub"] == "7"
    assert "password" not in claims
    assert client.get_cookie("session") is None
    params = app.test_dal.get_scalar.call_args.args[1]
    assert params == ("test@example.com",)


def test_wrong_password_does_not_issue_jwt(client, app):
    app.test_dal.get_scalar.return_value = None
    response = client.post(
        "/login", data={"email": "test@example.com", "password": "wrong"})
    assert b"Invalid Email or Password." in response.data
    assert client.get_cookie(COOKIE) is None


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
    assert client.get_cookie(COOKIE) is None


def test_registration_forces_user_role_and_hashes_password(client, app, auth_claims):
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
    assert auth_claims()["sub"] == "8"
    assert auth_claims()["role"] == 2


def test_logout_clears_cookie_and_revokes_token(client, sign_in, auth_claims, no_redis):
    from utils.auth_token import revocation_key

    sign_in()
    claims = auth_claims()
    token = client.get_cookie(COOKIE).value
    assert client.post("/logout").status_code == 302
    assert client.get_cookie(COOKIE) is None
    no_redis.set.assert_called_once_with(revocation_key(claims), "1", exat=claims["exp"])
    no_redis.exists.return_value = 1
    client.set_cookie(COOKIE, token)
    assert client.get("/vacations").location == "/login"
    no_redis.exists.assert_called_once_with(revocation_key(claims))


def test_login_rotates_jwt_and_csrf_claims(client, app, sign_in, auth_claims):
    sign_in()
    previous = auth_claims()
    app.test_dal.get_scalar.return_value = dict(
        id=7, first_name="Test", last_name="User", password=Security.hash("Abc123"), role=2)
    assert client.post("/login", data={"email": "test@example.com", "password": "Abc123"}).status_code == 302
    claims = auth_claims()
    assert claims["sub"] == "7"
    assert claims["jti"] != previous["jti"]
    assert claims["csrf"] != previous["csrf"]


@pytest.mark.parametrize("invalid", ["expired", "tampered", "wrong_audience"])
def test_invalid_jwt_clears_cookie_before_account_lookup(client, app, sign_in, auth_claims, invalid):
    import jwt

    sign_in()
    claims = auth_claims()
    if invalid == "expired":
        claims["exp"] = claims["iat"]
    elif invalid == "wrong_audience":
        claims["aud"] = "another-service"
    key = app.config["JWT_SECRET_KEY"] if invalid != "tampered" else "a-different-jwt-signing-key-for-tests"
    client.set_cookie(COOKIE, jwt.encode(claims, key, algorithm="HS256"))
    assert client.get("/vacations").location == "/login"
    assert client.get_cookie(COOKIE) is None
    app.test_account_lookup.assert_not_called()
