# Django test suite

From `Django/`:

```powershell
python -m venv env
./env/Scripts/python -m pip install -r requirements-dev.txt
./env/Scripts/python -m pytest
./env/Scripts/python -m pytest --cov=api --cov=users --cov=vacations --cov=likes --cov=utils --cov-report=term-missing
```

On Linux/macOS use `env/bin/python` instead of `env/Scripts/python`.

The suite uses test credentials and an in-memory SQLite database. It does not
load the repository `.env`, require a running Docker/MySQL service, or modify production data.
Development requirements include production dependencies, so installing them may
require MySQL client build prerequisites for `mysqlclient`.
All five shared tables (roles, users, countries, vacations, and likes) are unmanaged
by Django and explicitly created only in the isolated test database.
Endpoint tests exercise real middleware, JWT verification, ORM queries, aggregation,
and serialization. SQLite does not verify MySQL-specific schema or deployment behavior.

For real MySQL/schema and Redis coverage, run the separate
[MySQL integration suite](../../tests/mysql/README.md) from the repository root.

Like tests cover multiple vacations per user, duplicate-pair rejection, deletion
of individual likes, and statistics aggregation. The unmanaged likes model maps
the existing MySQL composite primary key `(user_id, vacation_id)`.

Password tests cover randomized hashing, shared Flask/Django compatibility,
legacy hash upgrades, rejected passwords, and malformed hashes.
Use pytest from this directory; `manage.py test` does not collect this suite.

Auth tests include enforced CSRF,
database-backed access validation, Redis refresh rotation/revocation, current-user checks,
Redis account disabling and status version changes across access/refresh tokens,
and absolute expiry. Redis tests use isolated fakeredis with Lua support; no real
Redis service is contacted.

For real Redis concurrency, TTL, revocation, and outage coverage, use
[`tests/redis`](../../tests/redis/README.md) from the repository root.
