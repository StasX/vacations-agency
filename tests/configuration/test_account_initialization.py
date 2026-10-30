"""Standalone provisioning tests; neither web application is imported."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/account-status/initialize.py'
spec = spec_from_file_location('account_initializer', SCRIPT)
initializer = module_from_spec(spec)
spec.loader.exec_module(initializer)


def database_with_users(*ids):
    database = MagicMock()
    cursor = database.cursor.return_value.__enter__.return_value
    cursor.__iter__.side_effect = lambda: iter((user_id,) for user_id in ids)
    return database


def redis_with_statuses(statuses):
    redis = MagicMock()
    def set_status(key, value, *, nx):
        assert nx is True
        if key in statuses:
            return False
        statuses[key] = value
        return True
    redis.set.side_effect = set_status
    return redis


def test_fresh_database_users_are_enabled_and_reruns_preserve_versions():
    statuses = {}
    redis = redis_with_statuses(statuses)
    database = database_with_users(1, 2, 9, 10)
    assert initializer.initialize_accounts(database, redis) == 4
    database.cursor.return_value.__enter__.return_value.execute.assert_called_with('SELECT id FROM users')
    for user_id in (1, 2, 9, 10):
        status = statuses[f'vacations:auth:status:{user_id}']
        assert status.startswith('enabled:')
        assert UUID(status.removeprefix('enabled:')).version == 4
    original = statuses.copy()
    assert initializer.initialize_accounts(database, redis) == 0
    assert statuses == original


@pytest.mark.parametrize('status', ['disabled:review-required', 'malformed', 'enabled:existing'])
def test_existing_status_is_never_overwritten(status):
    statuses = {'vacations:auth:status:1': status}
    assert initializer.initialize_accounts(database_with_users(1), redis_with_statuses(statuses)) == 0
    assert statuses == {'vacations:auth:status:1': status}


def test_empty_database_creates_no_status():
    redis = MagicMock()
    assert initializer.initialize_accounts(database_with_users(), redis) == 0
    redis.set.assert_not_called()


def test_redis_failure_stops_initialization():
    redis = MagicMock()
    redis.set.side_effect = RuntimeError('Redis unavailable')
    with pytest.raises(RuntimeError, match='Redis unavailable'):
        initializer.initialize_accounts(database_with_users(1), redis)


def test_database_failure_stops_before_status_changes():
    database = database_with_users(1)
    database.cursor.return_value.__enter__.return_value.execute.side_effect = RuntimeError('MySQL unavailable')
    redis = MagicMock()
    with pytest.raises(RuntimeError, match='MySQL unavailable'):
        initializer.initialize_accounts(database, redis)
    redis.set.assert_not_called()
