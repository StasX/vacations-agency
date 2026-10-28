# Shared database ownership and migrations

## Schema owner

The MySQL service owns the shared schema. Its definition and initial data are in
[`MySQL/data.sql`](../MySQL/data.sql), copied by
[`MySQL/Dockerfile`](../MySQL/Dockerfile) into `/docker-entrypoint-initdb.d/`.
Flask and Django consume the same tables in `vacation_agency`; neither backend
is the migration authority for those tables.

The deployment operator applies schema changes once per shared database, before
deploying code that requires them. Application startup does not run migrations.
[`MySQL/migrate.py`](../MySQL/migrate.py) applies numbered migrations and records
their version, filename, SHA-256 checksum, state, and timestamps in the shared
`schema_migrations` ledger. This ledger is owned by the migration tool, not either
backend. Django application migration directories contain only `__init__.py`.

## Table responsibilities

Schema ownership applies to all five tables. Runtime data responsibilities differ:

| Table | Flask | Django statistics service | Schema definition |
| --- | --- | --- | --- |
| `roles` | Reads role IDs for authorization | Reads administrator role for authentication and token validation | MySQL SQL script |
| `users` | Registers customers, reads accounts, upgrades legacy password hashes on login | Reads accounts and counts, validates current account state, upgrades legacy password hashes on login | MySQL SQL script |
| `countries` | Reads destination choices and names | Reads destination names for statistics | MySQL SQL script |
| `vacations` | Adds, updates, deletes, and lists vacations through administrator/customer flows | Reads and aggregates vacation dates and destinations | MySQL SQL script |
| `likes` | Inserts/deletes customer likes and reads counts | Reads total likes and likes by destination | MySQL SQL script |

Roles and countries are provisioned by SQL; neither application currently exposes
a management flow for their definitions. Django is not entirely read-only:
successful authentication may update `users.password` to the shared password format.
Both backends must remain compatible with that format.

Vacation image files belong to Flask and its `vacation-images` volume. MySQL stores
their filenames. Redis stores shared account-status versions and Django refresh
token records; these are not MySQL tables or Django migrations. See the repository
README's password-storage section for account-status provisioning and recovery.

## Django model mappings

All five shared models (`RoleModel`, `UserModel`, `CountryModel`, `VacationModel`,
and `LikeModel`) explicitly set `managed = False`. Django maps and queries the
existing tables without owning their creation, alteration, or deletion. ORM writes,
including password hash upgrades, still work. Schema changes belong to the shared
database migration tool.

Do not generate or apply Django migrations that create, alter, or delete the shared
tables. Review any `makemigrations` output for `users`, `vacations`, and `likes`
against the SQL-owned schema. A future switch to Django migration ownership must
explicitly reconcile all five existing tables and coordinate both applications.

Django's built-in auth/admin/session tables are separate from these shared domain
tables. If those features require database migrations, review and apply their
migration plan separately; do not use that as a reason to recreate shared tables.

## Fresh installation versus existing database

The SQL initialization script runs when MySQL initializes an empty data directory.
Normal application Compose runs preserve that directory in `vacations-volume`.
Changing `data.sql`, rebuilding the image, or restarting containers does not upgrade
an existing volume. `CREATE TABLE IF NOT EXISTS` does not reconcile existing columns
or constraints. Do not delete the database volume to deliver a schema update.

Use the explicit Compose maintenance service for both existing and freshly
initialized databases. It defaults to a plan and never replays seed data:

```sh
docker compose build database-migrations
docker compose run --rm database-migrations --plan
# After backup and review of the plan:
docker compose run --rm database-migrations --apply
```

The service uses the deployment's MySQL environment settings, connects internally
to `vacations-database`, and requires permission to alter the affected tables and
create/update its ledger. It is in the `tools` profile and is not run by normal
`docker compose up`. It does not mount or replace the database volume. `--plan`
reads the schema/history without creating a ledger or changing data; both modes
use a database-specific advisory lock to serialize migration runners.

Migration `0001__password_hash_capacity.py` verifies the five shared tables exist
and widens a legacy non-null `VARCHAR` password column to 128 characters when
needed. Existing values and wider columns are retained. A fresh/current schema is
recorded as applied without altering the column. This is a targeted upgrade,
not an automatic repair of arbitrary schema differences; unsupported column types
or nullability stop the migration for review. It does not reset passwords or
provision Redis statuses.

For each subsequent change, use this deployment procedure:

1. Define one reviewed upgrade for the shared database. Add the next numbered
   `NNNN__description.py` file under `MySQL/migrations/`, implementing
   `upgrade(connection)` with explicit SQL and schema checks. Document its
   source/target schema, backfill, compatibility, restartability, and recovery.
   Never edit, remove, or renumber a recorded migration; add a new version instead.
2. Update `MySQL/data.sql` to represent the resulting schema for fresh installations.
   Update Flask SQL and Django model mappings together, including column lengths,
   foreign keys, nullability, collation, and the composite likes primary key
   `(user_id, vacation_id)`.
3. Test both a fresh SQL initialization and the upgrade against a copy of the old
   schema with representative data. Run both backends' real MySQL integration
   suites, migration tests, and browser tests. Migration tests include a populated
   legacy password-column upgrade and a current-schema baseline. Each new migration
   must add coverage for its own source schema and data; fresh initialization alone
   does not prove an existing-volume upgrade works.
4. Back up the target database and verify the recovery procedure. Back up Flask
   images as well when a change affects their filenames or records. Arrange a
   maintenance window or use an additive change compatible with both deployed
   backend versions; defer destructive cleanup until both have upgraded.
5. Have the deployment operator run `--plan`, then `--apply` against the intended
   database using the deployment's credential mechanism. The ledger records each
   completed migration; repeat runs skip it. Retain the output in the deployment
   record. Missing/changed recorded files and out-of-order versions block execution.
6. Verify the resulting schema, retained data, and both application flows before
   completing deployment. On failure, use the change's documented recovery plan;
   deploying an older application image alone does not restore a previous schema.

Do not rerun the full seed dump as an upgrade: it contains initial/demo data as well
as DDL. Do not have Flask and Django independently apply competing migrations to
the same tables.

## Interrupted migrations

The runner commits a `running` ledger entry before executing a migration and marks
it `applied` only after success. A crash or error leaves an incomplete entry and
blocks further runs, including later migrations. MySQL DDL can commit implicitly;
the runner does not claim to roll back schema changes automatically. See the
[MySQL implicit-commit reference](https://dev.mysql.com/doc/refman/26.7/en/implicit-commit.html).

Inspect the actual schema and data against the migration's recovery instructions.
After a reviewed repair, or confirmation that the unchanged migration can safely
resume, use its explicit version:

```sh
docker compose run --rm database-migrations --apply --retry-failed 0001
```

Retry still checks the original filename and checksum. Do not edit the failed
migration or manually mark it applied to bypass verification. Version 0001 can be
retried after an interrupted column widening: it checks the current width and
does not narrow an already upgraded column. Retain the wider column if rolling
back application code; shrinking it can truncate modern password hashes.

## Validation references

- [Real MySQL integration tests](../tests/mysql/README.md)
- [Browser-to-backend tests](../tests/browser/README.md)
- [Django isolated tests](../Django/tests/README.md): SQLite and test-only table
  setup are not the production schema provisioning mechanism.
