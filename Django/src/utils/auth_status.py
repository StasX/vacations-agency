"""Persistent Redis account status, shared with the Flask application."""
from uuid import uuid4


def status_key(user_id):
    if type(user_id) is not int or user_id <= 0:
        raise ValueError('Invalid user identifier')
    return f'vacations:auth:status:{user_id}'


def get_status(user_id):
    from . import refresh_tokens
    status = refresh_tokens.get_redis().get(status_key(user_id))
    return 'enabled:initial' if status is None else status


def is_enabled(status):
    return isinstance(status, str) and status.startswith('enabled:')


def set_enabled(user_id, enabled):
    from . import refresh_tokens
    if type(enabled) is not bool:
        raise ValueError('enabled must be a boolean')
    status = ('enabled:' if enabled else 'disabled:') + str(uuid4())
    # No TTL: expiry must never silently reactivate a disabled account.
    refresh_tokens.get_redis().set(status_key(user_id), status)
    return status
