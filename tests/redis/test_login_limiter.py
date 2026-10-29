from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from uuid import uuid4

from utils import login_limiter


def test_login_budget_is_atomic_with_production_acl_and_expires(redis_client, monkeypatch):
    email = f'{uuid4().hex}@test.example'
    address = uuid4().hex
    keys = [
        'vacations:auth:login:ip:' + sha256(address.encode()).hexdigest(),
        'vacations:auth:login:account:' + sha256(email.encode()).hexdigest(),
    ]
    monkeypatch.setattr(login_limiter, 'get_redis', lambda: redis_client)
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: login_limiter.retry_after(address, email), range(25)))
        assert results.count(0) == 10
        assert all(1 <= value <= 900 for value in results if value)
        deadlines = [redis_client.pexpiretime(key) for key in keys]
        assert login_limiter.retry_after(address, email.upper()) > 0
        assert [redis_client.pexpiretime(key) for key in keys] == deadlines
        # Production ACL permits SET with EX, not administrative expiry commands.
        for key in keys:
            redis_client.set(key, 10, px=500)
        assert login_limiter.retry_after(address, email) == 1
        import time
        time.sleep(0.6)
        assert login_limiter.retry_after(address, email) == 0
    finally:
        redis_client.delete(*keys)
