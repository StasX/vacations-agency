"""Read the account status shared with Django in Redis."""
from functools import lru_cache
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
    status = get_redis().get(f'vacations:auth:status:{user_id}')
    return 'enabled:initial' if status is None else status


def is_enabled(status):
    return isinstance(status, str) and status.startswith('enabled:')
