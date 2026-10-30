from io import StringIO

import pytest
from django.core.management import call_command
from redis.exceptions import ConnectionError

from utils import auth_status


@pytest.mark.django_db
def test_initialization_activates_missing_status_and_is_idempotent(user, redis_store, client):
    key = auth_status.status_key(user.pk)
    redis_store.delete(key)
    call_command('initialize_account_status', stdout=StringIO())
    status = redis_store.get(key)
    assert auth_status.is_enabled(status)
    assert redis_store.ttl(key) == -1
    call_command('initialize_account_status', stdout=StringIO())
    assert redis_store.get(key) == status
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json')
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize('status', ['disabled:review-required', 'malformed'])
def test_initialization_preserves_existing_status(user, redis_store, status):
    key = auth_status.status_key(user.pk)
    redis_store.set(key, status)
    call_command('initialize_account_status', stdout=StringIO())
    assert redis_store.get(key) == status


@pytest.mark.django_db
def test_initialization_fails_when_redis_is_unavailable(user, redis_store, monkeypatch):
    def unavailable(*args, **kwargs):
        raise ConnectionError('offline')
    monkeypatch.setattr(redis_store, 'set', unavailable)
    with pytest.raises(ConnectionError):
        call_command('initialize_account_status', stdout=StringIO())
