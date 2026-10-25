from pathlib import Path
import re

from utils.security import Security


def test_seed_accounts_have_independently_salted_password_hashes():
    sql = (Path(__file__).resolve().parents[2] / "Mysql/data.sql").read_text(encoding="utf-8")
    rows = sql.split("INSERT INTO `users`", 1)[1].split(";", 1)[0]
    passwords = re.findall(r"'([^']*)',\s*[12]\)", rows)
    assert len(passwords) == 4
    assert len(set(passwords)) == 4
    for password in passwords:
        assert password.startswith("pbkdf2_sha256$1000000$")
        assert len(password) <= 128
        assert Security.verify("Abc123", password)
        assert not Security.verify("wrong", password)
        assert not Security.verify(password, password)
