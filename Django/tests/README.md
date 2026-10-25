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
Unmanaged country, vacation, and like tables are created only in the test database.
Endpoint tests exercise real middleware, JWT verification, ORM queries, aggregation,
and serialization. SQLite does not verify MySQL-specific schema or deployment behavior.

Known defects are documented with strict `xfail` tests:
malformed login input, vacation error status,
and multiple likes per user. These appear as expected failures; once a defect is
fixed, remove its marker (an unexpected pass fails the suite).

Production source and existing placeholder `src/*/tests.py` files are unchanged.
Use pytest from this directory; `manage.py test` does not collect this suite.
