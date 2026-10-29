"""Atomic, shared login budgets. Never store credentials in Redis keys."""
from hashlib import sha256

WINDOW_SECONDS = 15 * 60
ACCOUNT_LIMIT = 10
IP_LIMIT = 100

# Check every budget before consuming any; blocked traffic cannot extend expiry.
SCRIPT = """
local retry = 0
for i, key in ipairs(KEYS) do
    if tonumber(redis.call('GET', key) or '0') >= tonumber(ARGV[i + 1]) then
        retry = math.max(retry, 1, redis.call('TTL', key))
    end
end
if retry > 0 then return retry end
for _, key in ipairs(KEYS) do
    local count = tonumber(redis.call('GET', key) or '0') + 1
    if count == 1 then
        redis.call('SET', key, count, 'EX', ARGV[1])
    else
        redis.call('SET', key, count, 'KEEPTTL')
    end
end
return 0
"""


def retry_after(address, email):
    """Return seconds to wait, or zero when this attempt is admitted."""
    keys = ['vacations:auth:login:ip:' + sha256((address or 'unknown').encode()).hexdigest()]
    limits = [IP_LIMIT]
    if isinstance(email, str) and email.strip():
        normalized = email.strip().casefold()
        keys.append('vacations:auth:login:account:' + sha256(normalized.encode()).hexdigest())
        limits.append(ACCOUNT_LIMIT)
    return int(get_redis().eval(SCRIPT, len(keys), *keys, WINDOW_SECONDS, *limits))


def get_redis():
    from . import refresh_tokens
    return refresh_tokens.get_redis()

