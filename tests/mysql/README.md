# Real MySQL integration tests

Run from the repository root with Docker Compose:

```sh
docker compose -p vacations-mysql-tests -f compose.mysql-tests.yml build
docker compose -p vacations-mysql-tests -f compose.mysql-tests.yml up -d --wait --wait-timeout 180 mysql redis
docker compose -p vacations-mysql-tests -f compose.mysql-tests.yml run --rm django-tests
docker compose -p vacations-mysql-tests -f compose.mysql-tests.yml run --rm flask-tests
docker compose -p vacations-mysql-tests -f compose.mysql-tests.yml down --volumes --remove-orphans
```

Run the Django and Flask runners sequentially; both reset the isolated database
between tests. Always run the final cleanup command, including after a failure.
The `mysql-integration` CI job runs these commands on every push and pull request.

This uses the application's `MySQL/Dockerfile`, `MySQL/data.sql`, Python dependency
files, real drivers, and production application code. Django uses the prebuilt SQL
tables directly, rather than pytest-django's generated SQLite schema. Flask uses
its real DAL and request teardown. Redis is real too, for Django authentication.

The separate Compose project has no published service ports or persistent MySQL
data volume. It supplies only test credentials and disables dotenv loading; it
does not reuse the application containers or `.env` credentials. Cleanup refuses
to run without the explicit integration flag and expected test host/user/database.

Coverage includes MySQL composite likes keys, duplicate/case-insensitive email
constraints, date/price round trips, aggregation, login/refresh with CSRF, Flask
validation and missing records, unchanged updates, and connection cleanup.
These complement the regular unit suites; they are not browser end-to-end tests.

The Flask runner also runs shared-schema migration tests: upgrade a populated
legacy password column while preserving all domain rows, baseline a current
schema, reject changed migration history, serialize concurrent runners, and
require explicit recovery after interrupted DDL. Migration tooling is copied into
the test image; it does not replay the seed dump to upgrade existing tables.

History-validation tests that do not need Docker can run independently:

```sh
python -m pytest -c tests/migrations/pytest.ini tests/migrations -q
```
