import importlib
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def no_database(monkeypatch):
    monkeypatch.setattr("utils.dal.mysql.connector.connect", MagicMock(
        side_effect=AssertionError("Tests must not connect to MySQL")
    ))


@pytest.fixture
def app(monkeypatch):
    # Patch before importing app: vacations_view opens a DAL at import time.
    # Every test gets a fresh mock; no real database connections are allowed.
    dal = MagicMock(return_value=MagicMock())
    for name in ("auth", "countries", "likes", "vacations"):
        module = importlib.import_module(f"logic.{name}_logic")
        monkeypatch.setattr(module, "DAL", dal)
    application = importlib.import_module("app").app
    from utils.app_config import AppConfig

    monkeypatch.setattr(AppConfig, "passwords_salt", "test-only-salt")
    dal.return_value.reset_mock()
    monkeypatch.setitem(application.config, "TESTING", True)
    monkeypatch.setitem(application.config, "SECRET_KEY", "test-only-secret")
    monkeypatch.setattr(application, "test_dal", dal.return_value, raising=False)
    yield application


@pytest.fixture
def image_directory(app, tmp_path, monkeypatch):
    monkeypatch.setattr(app, "root_path", str(tmp_path))
    directory = tmp_path / "static/images/vacations"
    directory.mkdir(parents=True)
    (directory.parent / "no_photo.jpg").write_bytes(b"fallback")
    return directory


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sign_in(client):
    def login(role=2):
        user = dict(id=7, first_name="Test", last_name="User",
                    email="test@example.com", role=role)
        with client.session_transaction() as session:
            session["current_user"] = user
        return user
    return login
