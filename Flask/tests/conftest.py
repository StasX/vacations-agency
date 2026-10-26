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
    # Dedicated CSRF tests enable protection; existing tests isolate route behavior.
    monkeypatch.setitem(application.config, "CSRF_ENABLED", False)
    monkeypatch.setitem(application.config, "SECRET_KEY", "test-only-secret")
    monkeypatch.setattr(application, "test_dal",
                        dal.return_value, raising=False)
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
def request_connections(app, monkeypatch):
    """Exercise real DAL lifecycle with only the MySQL driver mocked."""
    from utils.dal import DAL
    connections = []
    def connect(**kwargs):
        connection = MagicMock()
        connection.is_connected.return_value = True
        connection.cursor.return_value.fetchall.return_value = []
        connection.cursor.return_value.fetchone.return_value = {'image': None}
        connections.append(connection)
        return connection
    monkeypatch.setattr('utils.dal.mysql.connector.connect', connect)
    for name in ('auth', 'countries', 'likes', 'vacations'):
        monkeypatch.setattr(importlib.import_module(f'logic.{name}_logic'), 'DAL', DAL)
    return connections


@pytest.fixture
def sign_in(client):
    def login(role=2):
        user = dict(id=7, first_name="Test", last_name="User",
                    email="test@example.com", role=role)
        with client.session_transaction() as session:
            session["current_user"] = user
        return user
    return login


def make_image(color="red", image_format="JPEG"):
    from io import BytesIO
    from PIL import Image
    stream = BytesIO()
    Image.new("RGB", (2, 2), color).save(stream, format=image_format)
    return stream.getvalue()
