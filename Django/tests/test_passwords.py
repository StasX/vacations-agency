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


@pytest.mark.django_db
@pytest.mark.parametrize("password,allowed", [("Password123!", True), ("Wrong123", False)])
def test_legacy_login_upgrades_only_correct_password(client, user, password, allowed):
    legacy = sha512(("Password123!" + AppConfig.passwords_salt).encode()).hexdigest()
    user.password = legacy
    user.save(update_fields=["password"])
    response = client.post("/api/auth/login", {"email": user.email, "password": password}, content_type="application/json")
    user.refresh_from_db()
    if allowed:
        assert response.status_code == 200
        assert user.password != legacy and Security.verify(password, user.password)
        assert not Security.needs_rehash(user.password)
    else:
        assert response.status_code == 400
        assert user.password == legacy
        assert "refresh" not in response.cookies


@pytest.mark.django_db
def test_modern_login_does_not_rehash(client, user):
    original = user.password
    assert client.post("/api/auth/login", {"email": user.email, "password": "Password123!"}, content_type="application/json").status_code == 200
    user.refresh_from_db()
    assert user.password == original
