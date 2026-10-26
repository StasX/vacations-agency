"""Read the account status shared with Django in Redis."""
from functools import lru_cache
from uuid import UUID, uuid4
from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry
from utils.app_config import AppConfig


@lru_cache(maxsize=1)
def get_redis():
    return Redis.from_url(AppConfig.redis_url, password=AppConfig.redis_password,
                          decode_responses=True, socket_connect_timeout=2,
                          socket_timeout=2, retry=Retry(NoBackoff(), 0))


def get_status(user_id):
    if type(user_id) is not int or user_id <= 0:
        raise ValueError('Invalid user identifier')
    return get_redis().get(f'vacations:auth:status:{user_id}')


def is_enabled(status):
    if not isinstance(status, str) or not status.startswith('enabled:'):
        return False
    try:
        version = status.removeprefix('enabled:')
        parsed = UUID(version)
        return parsed.version == 4 and str(parsed) == version
    except ValueError:
        return False


def initialize_status(user_id):
    # Only new-account registration may provision status; never overwrite a disable.
    if type(user_id) is not int or user_id <= 0:
        raise ValueError('Invalid user identifier')
    get_redis().set(f'vacations:auth:status:{user_id}', 'enabled:' + str(uuid4()), nx=True)
    return get_status(user_id)
