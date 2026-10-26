"""Persistent Redis account status, shared with the Flask application."""
from uuid import UUID, uuid4


def status_key(user_id):
    if type(user_id) is not int or user_id <= 0:
        raise ValueError('Invalid user identifier')
    return f'vacations:auth:status:{user_id}'


def get_status(user_id):
    from . import refresh_tokens
    return refresh_tokens.get_redis().get(status_key(user_id))


def is_enabled(status):
    if not isinstance(status, str) or not status.startswith('enabled:'):
        return False
    try:
        version = status.removeprefix('enabled:')
        parsed = UUID(version)
        return parsed.version == 4 and str(parsed) == version
    except ValueError:
        return False


def set_enabled(user_id, enabled):
    from . import refresh_tokens
    if type(enabled) is not bool:
        raise ValueError('enabled must be a boolean')
    status = ('enabled:' if enabled else 'disabled:') + str(uuid4())
    # No TTL: expiry must never silently reactivate a disabled account.
    refresh_tokens.get_redis().set(status_key(user_id), status)
    return status
