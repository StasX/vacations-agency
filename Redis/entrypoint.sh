#!/bin/sh
set -eu

: "${REDIS_PASSWORD:?REDIS_PASSWORD must be set}"
umask 077
# Hash the credential so it is absent from the ACL file and process arguments.
password_hash=$(printf '%s' "$REDIS_PASSWORD" | sha256sum | cut -d ' ' -f 1)
printf 'user default reset on #%s ~vacations:jwt:refresh:* ~vacations:auth:status:* -@all +@connection -client +client|setinfo +client|setname +get +set +del +eval +pexpiretime\n' \
    "$password_hash" > /tmp/redis-users.acl
unset password_hash

exec "$@"
