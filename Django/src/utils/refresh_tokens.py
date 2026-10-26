from functools import lru_cache
from hashlib import sha256

from django.conf import settings
from redis import Redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from .tokens import decode_token


# Consume the old JTI and register the new JTI atomically, preserving expiry.
ROTATE_SCRIPT = '''
local current = redis.call('GET', KEYS[1])
if not current or current ~= ARGV[1] then return 0 end
local deadline = redis.call('PEXPIRETIME', KEYS[1])
if deadline <= 0 then return 0 end
local created = redis.call('SET', KEYS[2], ARGV[2], 'PXAT', deadline, 'NX')
if not created then return 0 end
redis.call('DEL', KEYS[1])
return 1
'''


@lru_cache(maxsize=1)
def get_redis():
    return Redis.from_url(
        settings.JWT_REDIS_URL, decode_responses=True,
        password=settings.JWT_REDIS_PASSWORD,
        socket_connect_timeout=2, socket_timeout=2,
        # Retrying an ambiguously completed rotation can falsely detect replay.
        retry=Retry(NoBackoff(), 0),
    )


def token_key(claims):
    return 'vacations:jwt:refresh:' + claims['jti']


def fingerprint(token):
    return sha256(token.encode()).hexdigest()


def register(token):
    claims = decode_token(token)
    return bool(get_redis().set(token_key(claims), fingerprint(token),
                               exat=int(claims['exp']), nx=True))


def rotate(previous, replacement):
    claims = decode_token(previous)
    next_claims = decode_token(replacement)
    return bool(get_redis().eval(ROTATE_SCRIPT, 2, token_key(claims), token_key(next_claims),
                                fingerprint(previous), fingerprint(replacement)))


def revoke(token):
    claims = decode_token(token)
    if claims.get('type') == 'refresh':
        get_redis().delete(token_key(claims))
