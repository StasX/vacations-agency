from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.utils import timezone
from redis.exceptions import ConnectionError

from utils import refresh_tokens
from utils.tokens import decode_token, issue_tokens


def test_redis_stores_only_fingerprint_with_absolute_expiry(user, redis_store):
    _, token, expiry = issue_tokens(user, timezone.now() + timedelta(seconds=90))
    assert refresh_tokens.register(token)
    key = refresh_tokens.token_key(decode_token(token))
    assert redis_store.get(key) == refresh_tokens.fingerprint(token)
    assert redis_store.expiretime(key) == int(expiry.timestamp())
    assert not refresh_tokens.register(token)


def test_rotation_is_atomic_and_preserves_deadline(user, redis_store):
    _, original, expiry = issue_tokens(user)
    claims = decode_token(original)
    _, replacement, _ = issue_tokens(user, expiry, claims['sid'])
    refresh_tokens.register(original)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: refresh_tokens.rotate(original, replacement), range(2)))
    assert sorted(results) == [False, True]
    # The second use revokes the family, including the winner's replacement.
    assert not refresh_tokens.rotate(replacement, original)


def test_rotation_keeps_ttl_and_unknown_tokens_cannot_register_themselves(user, redis_store):
    _, original, expiry = issue_tokens(user)
    claims = decode_token(original)
    _, replacement, _ = issue_tokens(user, expiry, claims['sid'])
    assert not refresh_tokens.rotate(original, replacement)
    refresh_tokens.register(original)
    key = refresh_tokens.token_key(claims)
    deadline = redis_store.expiretime(key)
    assert refresh_tokens.rotate(original, replacement)
    assert redis_store.expiretime(key) == deadline


@pytest.mark.parametrize('operation', ['login', 'refresh-token', 'logout'])
def test_redis_outage_fails_closed(client, user, redis_store, monkeypatch, operation):
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    assert response.status_code == 200
    def unavailable():
        raise ConnectionError('store offline')
    monkeypatch.setattr(refresh_tokens, 'get_redis', unavailable)
    if operation == 'login':
        response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                               content_type='application/json')
    elif operation == 'logout':
        response = client.delete('/api/auth/logout')
    else:
        response = client.post('/api/auth/refresh-token')
    assert response.status_code == 503
    assert response.json() == {'error': 'Authentication temporarily unavailable'}
    assert response['Retry-After'] == '5'
    assert 'access_token' not in response.json()
    assert 'refresh' not in response.cookies


def test_logout_revokes_latest_refresh_using_an_older_family_token(client, user):
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    original = response.cookies['refresh'].value
    latest = client.post('/api/auth/refresh-token').cookies['refresh'].value
    client.cookies['refresh'] = original
    assert client.delete('/api/auth/logout').status_code == 204
    client.cookies['refresh'] = latest
    assert client.post('/api/auth/refresh-token').status_code == 401


def test_refresh_keys_expire_and_missing_state_is_rejected(client, user, redis_store):
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    claims = decode_token(response.cookies['refresh'].value)
    redis_store.pexpire(refresh_tokens.token_key(claims), 0)
    assert client.post('/api/auth/refresh-token').status_code == 401


def test_valid_but_unregistered_refresh_is_rejected(client, user):
    _, token, _ = issue_tokens(user)
    client.cookies['refresh'] = token
    assert client.post('/api/auth/refresh-token').status_code == 401


def test_new_login_revokes_previous_browser_refresh(client, user):
    credentials = {'email': user.email, 'password': 'Password123!'}
    original = client.post('/api/auth/login', credentials, content_type='application/json').cookies['refresh'].value
    response = client.post('/api/auth/login', credentials, content_type='application/json')
    newest = response.cookies['refresh'].value
    client.cookies['refresh'] = original
    assert client.post('/api/auth/refresh-token').status_code == 401
    client.cookies['refresh'] = newest
    assert client.post('/api/auth/refresh-token').status_code == 200
