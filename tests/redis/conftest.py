"""Use the isolated Redis service, without Django's fakeredis/SQLite fixtures."""
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from urllib.parse import urlsplit

import pytest

url = urlsplit(os.environ.get('JWT_REDIS_URL', ''))
if (os.environ.get('REDIS_INTEGRATION_TESTS') != '1'
        or url.hostname != 'redis' or url.port != 6379 or url.path != '/0'):
    raise RuntimeError('Run these tests using compose.redis-tests.yml')

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'Django' / 'src'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'api.settings'
import django
django.setup()

from utils import refresh_tokens
from utils.tokens import decode_token, issue_tokens


@pytest.fixture
def redis_client():
    refresh_tokens.get_redis.cache_clear()
    client = refresh_tokens.get_redis()
    assert client.ping()
    yield client
    client.close()
    refresh_tokens.get_redis.cache_clear()


@pytest.fixture
def user():
    # Identity is synthetic: these tests exercise Redis and never open MySQL.
    return SimpleNamespace(pk=7, first_name='Redis', last_name='Tester',
        email='redis@test.example', password='test-only-password-hash',
        role=SimpleNamespace(role_type='Admin'))


@pytest.fixture
def token_factory(user, redis_client):
    keys = []
    def make(expires_at=None):
        _, token, _ = issue_tokens(user, expires_at)
        keys.append(refresh_tokens.token_key(decode_token(token)))
        return token
    yield make
    # Delete only this test's random JTIs; no FLUSHDB, KEYS, or broad cleanup.
    if keys:
        redis_client.delete(*keys)
