import pytest
from redis.exceptions import ConnectionError
from utils import auth_status


def test_status_persists_and_reenable_changes_version(redis_store):
    assert auth_status.get_status(7) is None
    assert not auth_status.is_enabled(auth_status.get_status(7))
    disabled = auth_status.set_enabled(7, False)
    assert not auth_status.is_enabled(disabled)
    assert auth_status.get_status(7) == disabled
    assert redis_store.ttl(auth_status.status_key(7)) == -1
    enabled = auth_status.set_enabled(7, True)
    assert auth_status.is_enabled(enabled)
    assert enabled != 'enabled:initial'
    assert auth_status.get_status(7) == enabled


@pytest.mark.parametrize('status', [None, '', 'enabled:', 'enabled:initial', 'enabled:invalid',
    'disabled:00000000-0000-4000-8000-000000000007'])
def test_missing_or_malformed_status_is_not_enabled(status):
    assert not auth_status.is_enabled(status)


@pytest.mark.django_db
@pytest.mark.parametrize('stored_status', [None, 'enabled:invalid', 'disabled:review-required'])
def test_login_explains_unavailable_account_without_changing_status(client, user, redis_store, stored_status):
    key = auth_status.status_key(user.pk)
    redis_store.delete(key)
    if stored_status is not None:
        redis_store.set(key, stored_status)
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    assert response.status_code == 403
    assert response.json()['code'] == 'account_unavailable'
    assert 'refresh' not in response.cookies
    assert redis_store.get(key) == stored_status
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'incorrect'},
                           content_type='application/json')
    assert response.status_code == 400
    assert response.json() == {'error': 'Wrong credentials'}


@pytest.mark.django_db
@pytest.mark.parametrize('operation', ['access', 'refresh', 'login'])
def test_deleted_disabled_status_never_reactivates_account(client, user, redis_store, operation):
    from utils.tokens import issue_tokens
    from utils import refresh_tokens
    access, refresh, _ = issue_tokens(user)
    refresh_tokens.register(refresh)
    auth_status.set_enabled(user.pk, False)
    redis_store.delete(auth_status.status_key(user.pk))
    if operation == 'access':
        response = client.get('/api/users/total', HTTP_AUTHORIZATION=access)
    elif operation == 'refresh':
        client.cookies['refresh'] = refresh
        response = client.post('/api/auth/refresh-token')
    else:
        response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                               content_type='application/json')
    assert response.status_code == (403 if operation == 'login' else 401)
    assert redis_store.get(auth_status.status_key(user.pk)) is None


@pytest.mark.parametrize('operation', ['access', 'refresh'])
@pytest.mark.django_db
def test_reenabled_account_cannot_reuse_old_tokens(client, user, operation):
    from utils.tokens import issue_tokens
    from utils import refresh_tokens
    access, refresh, _ = issue_tokens(user)
    refresh_tokens.register(refresh)
    auth_status.set_enabled(user.pk, False)
    auth_status.set_enabled(user.pk, True)
    if operation == 'access':
        response = client.get('/api/users/total', HTTP_AUTHORIZATION=access)
    else:
        client.cookies['refresh'] = refresh
        response = client.post('/api/auth/refresh-token')
    assert response.status_code == 401
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    assert response.status_code == 200
    assert client.get('/api/users/total', HTTP_AUTHORIZATION=response.json()['access_token']).status_code == 200


@pytest.mark.django_db
def test_access_rejects_redis_outage(client, user, redis_store, monkeypatch):
    from utils.tokens import issue_tokens
    access, _, _ = issue_tokens(user)
    def unavailable(*args):
        raise ConnectionError('offline')
    monkeypatch.setattr(redis_store, 'get', unavailable)
    response = client.get('/api/users/total', HTTP_AUTHORIZATION=access)
    assert response.status_code == 503
    assert response['Retry-After'] == '5'


@pytest.mark.django_db
def test_status_change_during_refresh_cannot_issue_current_version(client, user, monkeypatch):
    from utils import refresh_tokens
    from utils.tokens import issue_tokens
    _, refresh, _ = issue_tokens(user)
    refresh_tokens.register(refresh)
    client.cookies['refresh'] = refresh
    read_status = auth_status.get_status
    calls = 0
    def change_after_validation(user_id):
        nonlocal calls
        calls += 1
        if calls == 2:
            auth_status.set_enabled(user_id, False)
            auth_status.set_enabled(user_id, True)
        return read_status(user_id)
    monkeypatch.setattr(auth_status, 'get_status', change_after_validation)
    response = client.post('/api/auth/refresh-token')
    assert response.status_code == 401
    assert 'access_token' not in response.json()
