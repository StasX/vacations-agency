from utils.security import Security


def test_login_stores_user_without_password(client, app):
    app.test_dal.get_scalar.return_value = dict(
        id=7, first_name="Test", last_name="User", email="test@example.com",
        password="hashed", role=2,
    )
    response = client.post("/login", data={"email": "test@example.com", "password": "Abc123"})
    assert response.status_code == 302
    assert response.location == "/vacations"
    with client.session_transaction() as session:
        assert session["current_user"]["id"] == 7
        assert "password" not in session["current_user"]
    params = app.test_dal.get_scalar.call_args.args[1]
    assert params == ("test@example.com", Security.hash("Abc123"))


def test_wrong_password_does_not_create_session(client, app):
    app.test_dal.get_scalar.return_value = None
    response = client.post("/login", data={"email": "test@example.com", "password": "wrong"})
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


def test_registration_forces_user_role_and_hashes_password(client, app):
    app.test_dal.get_scalar.side_effect = [
        {"COUNT(*)": 0},
        dict(id=8, first_name="Test", last_name="User", email="test@example.com", password="hash", role=2),
    ]
    response = client.post("/register", data=dict(
        first_name="Test", last_name="User", email="test@example.com", password="Abc123", role=1
    ))
    assert response.status_code == 302
    params = app.test_dal.insert.call_args.args[1]
    assert params[-1] == 2
    assert params[-2] == Security.hash("Abc123")
    with client.session_transaction() as session:
        assert session["current_user"]["id"] == 8
        assert "password" not in session["current_user"]


def test_logout_clears_session(client, sign_in):
    sign_in()
    assert client.get("/logout").status_code == 302
    with client.session_transaction() as session:
        assert not session
