from concurrent.futures import ThreadPoolExecutor
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest
from redis.exceptions import ConnectionError

from utils import login_limiter


@pytest.fixture(params=['Flask', 'Django'])
def limiter(request, redis_store, monkeypatch):
    # Execute both independently packaged implementations against the same Redis API.
    path = Path(__file__).resolve().parents[2] / request.param / 'src/utils/login_limiter.py'
    spec = spec_from_file_location('tested_limiter', path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'get_redis', lambda: redis_store)
    return module


def test_account_budget_is_normalized_and_survives_client_changes(limiter, redis_store):
    for index in range(10):
        assert limiter.retry_after(str(index), ' Admin@Example.com ') == 0
    assert 1 <= limiter.retry_after('other', 'admin@example.com') <= 900
    assert limiter.retry_after('other', 'different@example.com') == 0
    assert all('example.com' not in key for key in redis_store.keys())


def test_ip_budget_covers_rotating_accounts_and_missing_email(limiter):
    for index in range(100):
        assert limiter.retry_after('127.0.0.1', f'{index}@example.com') == 0
    assert limiter.retry_after('127.0.0.1', None) > 0
    assert limiter.retry_after('127.0.0.2', None) == 0


def test_expiry_allows_recovery_and_blocking_does_not_extend_window(limiter, redis_store):
    for _ in range(10):
        assert limiter.retry_after('client', 'user@example.com') == 0
    keys = redis_store.keys('vacations:auth:login:*')
    deadlines = [redis_store.pexpiretime(key) for key in keys]
    assert limiter.retry_after('client', 'user@example.com') > 0
    assert [redis_store.pexpiretime(key) for key in keys] == deadlines
    for key in keys:
        redis_store.pexpire(key, 500)
    assert limiter.retry_after('client', 'user@example.com') == 1
    for key in keys:
        redis_store.expire(key, 0)
    assert limiter.retry_after('client', 'user@example.com') == 0


def test_concurrent_attempts_cannot_exceed_budget(limiter):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: limiter.retry_after('client', 'user@example.com'), range(25)))
    assert results.count(0) == 10


def test_django_blocks_before_authentication_and_ignores_forwarded_ip(client, monkeypatch):
    from unittest.mock import Mock
    authenticate = Mock()
    monkeypatch.setattr('api.views.authenticate', authenticate)
    monkeypatch.setattr(login_limiter, 'IP_LIMIT', 2)
    for index in range(2):
        assert client.post('/api/auth/login', '{}', content_type='application/json',
                           HTTP_X_FORWARDED_FOR=f'192.0.2.{index}').status_code == 400
    response = client.post('/api/auth/login', '{', content_type='application/json',
                           HTTP_X_FORWARDED_FOR='192.0.2.99')
    assert response.status_code == 429
    assert 1 <= int(response['Retry-After']) <= 900
    authenticate.assert_not_called()


def test_django_limiter_outage_fails_closed(client, monkeypatch):
    def unavailable(*args):
        raise ConnectionError('offline')
    monkeypatch.setattr(login_limiter, 'retry_after', unavailable)
    response = client.post('/api/auth/login', '{}', content_type='application/json')
    assert response.status_code == 503
    assert response['Retry-After'] == '5'
