from functools import lru_cache
from hashlib import sha256

from django.conf import settings
from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from .tokens import decode_token


# Compare and replace atomically across all workers; preserve the original TTL.
# A replay deletes the family so its newest refresh token is rejected too.
ROTATE_SCRIPT = '''
local current = redis.call('GET', KEYS[1])
if not current then return 0 end
if current ~= ARGV[1] then
    redis.call('DEL', KEYS[1])
    return 0
end
redis.call('SET', KEYS[1], ARGV[2], 'KEEPTTL')
return 1
'''


@lru_cache(maxsize=1)
def get_redis():
    return Redis.from_url(
        settings.JWT_REDIS_URL, decode_responses=True,
        socket_connect_timeout=2, socket_timeout=2,
        # Retrying an ambiguously completed rotation can falsely detect replay.
        retry=Retry(NoBackoff(), 0),
    )


def token_key(claims):
    return 'vacations:jwt:refresh:' + claims['sid']


def fingerprint(token):
    return sha256(token.encode()).hexdigest()


def register(token):
    claims = decode_token(token)
    return bool(get_redis().set(token_key(claims), fingerprint(token),
                               exat=int(claims['exp']), nx=True))


def rotate(previous, replacement):
    claims = decode_token(previous)
    return bool(get_redis().eval(ROTATE_SCRIPT, 1, token_key(claims),
                                fingerprint(previous), fingerprint(replacement)))


def revoke(token):
    claims = decode_token(token)
    if claims.get('type') == 'refresh':
        get_redis().delete(token_key(claims))
