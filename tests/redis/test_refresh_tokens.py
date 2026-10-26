from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
from threading import Barrier
import time

import pytest
from django.test import RequestFactory, override_settings
from django.utils import timezone

from utils import refresh_tokens
from utils.tokens import decode_token


def test_register_tracks_jti_hash_and_absolute_expiry(redis_client, token_factory):
    token = token_factory(timezone.now() + timedelta(seconds=90))
    claims = decode_token(token)
    key = refresh_tokens.token_key(claims)
    assert key == 'vacations:jwt:refresh:' + claims['jti']
    assert refresh_tokens.register(token)
    assert redis_client.get(key) == refresh_tokens.fingerprint(token)
    assert redis_client.pexpiretime(key) == int(claims['exp']) * 1000
    assert not refresh_tokens.register(token)


def test_concurrent_rotation_has_exactly_one_winner(redis_client, token_factory):
    expiry = timezone.now() + timedelta(minutes=5)
    original = token_factory(expiry)
    replacements = [token_factory(expiry) for _ in range(8)]
    assert refresh_tokens.register(original)
    barrier = Barrier(len(replacements))
    def rotate(token):
        barrier.wait(timeout=10)
        return refresh_tokens.rotate(original, token)
    with ThreadPoolExecutor(max_workers=len(replacements)) as pool:
        results = list(pool.map(rotate, replacements))
    assert results.count(True) == 1
    assert redis_client.get(refresh_tokens.token_key(decode_token(original))) is None
    for token, won in zip(replacements, results):
        value = redis_client.get(refresh_tokens.token_key(decode_token(token)))
        assert value == (refresh_tokens.fingerprint(token) if won else None)


def test_rotation_preserves_deadline_and_rejects_replay(redis_client, token_factory):
    original, replacement, other = [token_factory() for _ in range(3)]
    assert refresh_tokens.register(original)
    deadline = redis_client.pexpiretime(refresh_tokens.token_key(decode_token(original)))
    assert refresh_tokens.rotate(original, replacement)
    assert redis_client.pexpiretime(refresh_tokens.token_key(decode_token(replacement))) == deadline
    assert not refresh_tokens.rotate(original, other)
    assert redis_client.get(refresh_tokens.token_key(decode_token(other))) is None
    assert redis_client.get(refresh_tokens.token_key(decode_token(replacement))) == refresh_tokens.fingerprint(replacement)


def test_logout_revokes_presented_jti_without_affecting_other_tokens(redis_client, token_factory):
    from api.views import logout
    token, other, replacement = [token_factory() for _ in range(3)]
    assert refresh_tokens.register(token)
    assert refresh_tokens.register(other)
    request = RequestFactory().delete('/api/auth/logout')
    request.COOKIES['refresh'] = token
    request._dont_enforce_csrf_checks = True
    response = logout(request)
    assert response.status_code == 204
    assert response.cookies['refresh']['max-age'] == 0
    assert not refresh_tokens.rotate(token, replacement)
    assert redis_client.get(refresh_tokens.token_key(decode_token(other))) == refresh_tokens.fingerprint(other)


def test_missing_and_expired_jtis_cannot_issue_replacements(redis_client, token_factory):
    original, replacement = token_factory(), token_factory()
    assert not refresh_tokens.rotate(original, replacement)
    key = refresh_tokens.token_key(decode_token(original))
    # Expire Redis state while keeping the signed JWT valid.
    redis_client.set(key, refresh_tokens.fingerprint(original), px=50)
    deadline = time.monotonic() + 2
    while redis_client.get(key) is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    assert redis_client.get(key) is None
    assert not refresh_tokens.rotate(original, replacement)
    assert redis_client.get(refresh_tokens.token_key(decode_token(replacement))) is None


def test_mismatched_fingerprint_cannot_consume_token(redis_client, token_factory):
    original, replacement = token_factory(), token_factory()
    assert refresh_tokens.register(original)
    key = refresh_tokens.token_key(decode_token(original))
    redis_client.set(key, 'wrong-fingerprint', keepttl=True)
    assert not refresh_tokens.rotate(original, replacement)
    assert redis_client.get(key) == 'wrong-fingerprint'
    assert redis_client.get(refresh_tokens.token_key(decode_token(replacement))) is None


@pytest.mark.parametrize('operation', ['login', 'refresh_token', 'logout'])
def test_unreachable_redis_returns_503_without_issuing_tokens(
        redis_client, token_factory, user, monkeypatch, operation):
    from api import views
    from types import SimpleNamespace
    token = token_factory()
    assert refresh_tokens.register(token)
    # Supply identity without a database; Redis connections are never mocked.
    monkeypatch.setattr(views, 'authenticate', lambda *args, **kwargs: user)
    monkeypatch.setattr(views.UserModel.objects, 'select_related',
                        lambda *args: SimpleNamespace(get=lambda **kwargs: user))
    factory = RequestFactory()
    if operation == 'logout':
        request = factory.delete('/api/auth/logout')
    else:
        request = factory.post('/api/auth/' + operation,
            {'email': user.email, 'password': 'test-password'}, content_type='application/json')
    if operation != 'login':
        request.COOKIES['refresh'] = token
    request._dont_enforce_csrf_checks = True
    refresh_tokens.get_redis.cache_clear()
    with override_settings(JWT_REDIS_URL='redis://127.0.0.1:1/0'):
        try:
            response = getattr(views, operation)(request)
        finally:
            refresh_tokens.get_redis().close()
            refresh_tokens.get_redis.cache_clear()
    assert response.status_code == 503
    assert json.loads(response.content) == {'error': 'Authentication temporarily unavailable'}
    assert response['Retry-After'] == '5'
    assert 'refresh' not in response.cookies
    assert redis_client.get(refresh_tokens.token_key(decode_token(token))) == refresh_tokens.fingerprint(token)
