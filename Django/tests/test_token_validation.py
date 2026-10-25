import jwt
import pytest

from utils.app_config import AppConfig


@pytest.mark.parametrize("refresh", [False, True])
@pytest.mark.parametrize("defect", ["wrong-issuer", "algorithm", "exp", "iat", "iss", "aud", "jti", "type", "user"])
def test_invalid_session_claims_are_rejected(client, token_factory, refresh, defect):
    payload = jwt.decode(token_factory(type="refresh" if refresh else "access"),
                         options={"verify_signature": False})
    algorithm = "HS256"
    if defect == "wrong-issuer":
        payload["iss"] = "untrusted-issuer"
    elif defect == "algorithm":
        algorithm = "HS512"
    else:
        del payload[defect]
    token = jwt.encode(payload, AppConfig.secret_key, algorithm=algorithm)
    if refresh:
        client.cookies["refresh"] = token
        response = client.get("/api/auth/refresh-token")
        assert "refresh" not in response.cookies
    else:
        response = client.get("/api/users/total", HTTP_AUTHORIZATION=token)
    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}


@pytest.mark.parametrize("credentials", [{}, {"email": [], "password": "secret"},
    {"email": "admin@example.com", "password": []},
    {"email": " ", "password": "secret"}, {"email": "admin@example.com", "password": ""}])
def test_invalid_credentials_are_rejected_before_authentication(client, monkeypatch, credentials):
    def unexpected_authentication(*args, **kwargs):
        pytest.fail("Invalid credentials must not reach authentication")
    monkeypatch.setattr("api.views.authenticate", unexpected_authentication)
    response = client.post("/api/auth/login", credentials, content_type="application/json")
    assert response.status_code == 400
    assert "refresh" not in response.cookies


def test_refreshed_cookie_matches_token_lifetime(client, token_factory):
    client.cookies["refresh"] = token_factory(type="refresh")
    response = client.get("/api/auth/refresh-token")
    assert response.status_code == 200
    assert response.cookies["refresh"]["max-age"] == 3600
