# Real Redis refresh-token tests

From the repository root:

```sh
docker compose -p vacations-redis-tests -f compose.redis-tests.yml build
docker compose -p vacations-redis-tests -f compose.redis-tests.yml run --rm redis-tests
docker compose -p vacations-redis-tests -f compose.redis-tests.yml down --volumes --remove-orphans
```

The suite uses the application's hardened Redis image and real Redis client/Lua
operations. It reuses the Django test-runner image definition in
`tests/mysql/Dockerfile`, but starts no MySQL service and performs no SQL queries.
No service ports are published. Data lives in temporary container storage, and
cleanup deletes only each test's random JTI keys. Always run the final command,
including after failures.

Coverage: JTI fingerprints and expiry, eight concurrent rotations with exactly one
winner, replay rejection, logout revocation, expiry/missing keys, mismatched
fingerprints, and HTTP 503 responses when Redis is unreachable. Outage tests
connect to an unused local port; Redis clients and commands are not mocked.
Synthetic identity replaces authentication/database reads in those tests only.

These tests complement Django's fast fakeredis suite and the MySQL integration
suite. They run separately in the `redis-integration` CI job.
