from hashlib import sha512
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from utils.app_config import AppConfig
from utils.security import Security


@pytest.mark.parametrize("stored", [None, "bad", "pbkdf2_sha256$bad$salt$hash",
                                     "pbkdf2_sha256$0$salt$hash", "pbkdf2_sha256$999999999$salt$hash"])
def test_invalid_hashes_are_rejected(stored):
    assert not Security.verify("password", stored)


def test_both_backends_share_password_format():
    root = Path(__file__).resolve().parents[2]
    other = "Django" if "Flask" in str(Path(__file__).parent.parent) else "Flask"
    spec = spec_from_file_location("utils.other_security", root / other / "src/utils/security.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    password = "Password123!"
    assert module.Security.verify(password, Security.hash(password))
    assert Security.verify(password, module.Security.hash(password))


@pytest.mark.parametrize("password,allowed", [("Abc123", True), ("Wrong123", False)])
def test_legacy_login_upgrades_only_correct_password(client, app, password, allowed):
    legacy = sha512(("Abc123" + AppConfig.passwords_salt).encode()).hexdigest()
    app.test_dal.get_scalar.return_value = dict(
        id=7, first_name="Test", last_name="User", email="test@example.com", password=legacy, role=2)
    response = client.post("/login", data={"email": "test@example.com", "password": password})
    if allowed:
        assert response.status_code == 302
        sql, (new_hash, user_id) = app.test_dal.update.call_args.args
        assert user_id == 7 and "UPDATE users" in sql
        assert new_hash != legacy and Security.verify(password, new_hash)
        assert not Security.needs_rehash(new_hash)
    else:
        assert b"Invalid Email or Password" in response.data
        app.test_dal.update.assert_not_called()
        with client.session_transaction() as session:
            assert "current_user" not in session


def test_modern_login_does_not_rehash(client, app):
    app.test_dal.get_scalar.return_value = dict(
        id=7, first_name="Test", last_name="User", password=Security.hash("Abc123"), role=2)
    assert client.post("/login", data={"email": "test@example.com", "password": "Abc123"}).status_code == 302
    app.test_dal.update.assert_not_called()
