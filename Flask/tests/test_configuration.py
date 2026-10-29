from pathlib import Path
import runpy
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"


@pytest.mark.parametrize("value, expected", [(None, False), ("true", True), (" YES ", True), ("false", False), ("0", False)])
def test_session_cookie_secure_environment(monkeypatch, value, expected):
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.setattr("dotenv.load_dotenv", lambda: None)
    monkeypatch.delenv("FLASK_COOKIE_SECURE", raising=False)
    if value is not None:
        monkeypatch.setenv("FLASK_COOKIE_SECURE", value)
    config = runpy.run_path(str(SRC / "utils/app_config.py"))["AppConfig"]
    assert config.session_cookie_secure is expected


def test_production_profile_enforces_secure_defaults(monkeypatch):
    monkeypatch.setattr('dotenv.load_dotenv', lambda: None)
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.setenv('FLASK_COOKIE_SECURE', 'false')
    monkeypatch.setenv('FLASK_DEBUG', 'true')
    config = runpy.run_path(str(SRC / 'utils/app_config.py'))['AppConfig']
    assert config.session_cookie_secure is True
    assert config.flask_config.DEBUG is False
    assert config.flask_config.CSRF_ENABLED is True


def test_development_profile_preserves_csrf(monkeypatch):
    monkeypatch.setattr('dotenv.load_dotenv', lambda: None)
    monkeypatch.setenv('APP_ENV', 'development')
    monkeypatch.delenv('FLASK_COOKIE_SECURE', raising=False)
    config = runpy.run_path(str(SRC / 'utils/app_config.py'))['AppConfig']
    assert config.flask_config.DEBUG is True
    assert config.session_cookie_secure is False
    assert config.flask_config.CSRF_ENABLED is True


def test_unknown_profile_rejected(monkeypatch):
    monkeypatch.setattr('dotenv.load_dotenv', lambda: None)
    monkeypatch.setenv('APP_ENV', 'prodution')
    with pytest.raises(ValueError, match='APP_ENV'):
        runpy.run_path(str(SRC / 'utils/app_config.py'))


@pytest.mark.parametrize("secure", [True, False])
def test_session_cookie_headers(app, monkeypatch, secure):
    from flask import session

    monkeypatch.setitem(app.config, "SESSION_COOKIE_SECURE", secure)
    with app.test_request_context("/", base_url="https://localhost"):
        session["current_user"] = {"id": 7}
        response = app.process_response(app.response_class())
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert ("Secure" in cookie) is secure


def test_configuration_reads_environment(monkeypatch):
    expected = {
        "MYSQL_HOST": "test-host", "MYSQL_USER": "test-user", "MYSQL_PASSWORD": "test-password",
        "MYSQL_DATABASE": "test-db", "SESSION_SECRET_KEY": "test-secret", "PASSWORDS_SALT": "test-salt",
    }
    for key, value in expected.items():
        monkeypatch.setenv(key, value)
    # Execute in an isolated namespace so imported application config isn't changed.
    config = runpy.run_path(str(SRC / "utils/app_config.py"))["AppConfig"]
    for attribute, key in [
        ("mysql_host", "MYSQL_HOST"), ("mysql_user", "MYSQL_USER"),
        ("mysql_password", "MYSQL_PASSWORD"), ("mysql_database", "MYSQL_DATABASE"),
        ("session_secret_key", "SESSION_SECRET_KEY"), ("passwords_salt", "PASSWORDS_SALT"),
    ]:
        assert getattr(config, attribute) == expected[key]


def test_gunicorn_defaults(monkeypatch):
    monkeypatch.delenv("APP_HOST", raising=False)
    monkeypatch.delenv("GUNICORN_WORKERS", raising=False)
    config = runpy.run_path(str(SRC / "gunicorn.conf.py"))
    assert config["bind"] == "0.0.0.0:5000"
    assert config["workers"] == 2
    assert config["timeout"] == 30
    assert config["preload_app"] is False


def test_gunicorn_environment_overrides(monkeypatch):
    monkeypatch.setenv("APP_HOST", "127.0.0.1")
    monkeypatch.setenv("GUNICORN_WORKERS", "4")
    config = runpy.run_path(str(SRC / "gunicorn.conf.py"))
    assert config["bind"] == "127.0.0.1:5000"
    assert config["workers"] == 4
