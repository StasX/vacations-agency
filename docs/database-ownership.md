# Shared database ownership and migrations

## Schema owner

The MySQL service owns the shared schema. Its definition and initial data are in
[`MySQL/data.sql`](../MySQL/data.sql), copied by
[`MySQL/Dockerfile`](../MySQL/Dockerfile) into `/docker-entrypoint-initdb.d/`.
Flask and Django consume the same tables in `vacation_agency`; neither backend
is the migration authority for those tables.

The deployment operator applies schema changes once per shared database, before
deploying code that requires them. Application startup does not run migrations.
There is currently no versioned SQL migration runner or migration-history table,
and the Django application migration directories contain only `__init__.py`.

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

## Django model caveat

`CountryModel`, `VacationModel`, and `LikeModel` explicitly set `managed = False`.
`RoleModel` and `UserModel` currently omit that setting, so Django considers them
managed. This is a configuration inconsistency, not an assignment of shared-schema
ownership to Django. This document does not change those model settings.

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

For an existing installation, use this deployment procedure:

1. Define one reviewed SQL upgrade for the shared database. Commit it as a numbered
   file under `MySQL/migrations/` when introducing the first change; that directory
   and its execution tooling do not exist yet. Document the source/target schema,
   data backfill, application compatibility, and recovery procedure with the change.
2. Update `MySQL/data.sql` to represent the resulting schema for fresh installations.
   Update Flask SQL and Django model mappings together, including column lengths,
   foreign keys, nullability, collation, and the composite likes primary key
   `(user_id, vacation_id)`.
3. Test both a fresh SQL initialization and the upgrade against a copy of the old
   schema with representative data. Run both backends' real MySQL integration
   suites and the browser tests. Their disposable databases currently test fresh
   initialization; they do not prove an existing-volume upgrade works.
4. Back up the target database and verify the recovery procedure. Back up Flask
   images as well when a change affects their filenames or records. Arrange a
   maintenance window or use an additive change compatible with both deployed
   backend versions; defer destructive cleanup until both have upgraded.
5. Have the deployment operator apply the reviewed SQL once to the intended
   database using the deployment's credential mechanism. Record the script version
   and result in the deployment record, since no automatic migration ledger exists.
6. Verify the resulting schema, retained data, and both application flows before
   completing deployment. On failure, use the change's documented recovery plan;
   deploying an older application image alone does not restore a previous schema.

Do not rerun the full seed dump as an upgrade: it contains initial/demo data as well
as DDL. Do not have Flask and Django independently apply competing migrations to
the same tables.

## Validation references

- [Real MySQL integration tests](../tests/mysql/README.md)
- [Browser-to-backend tests](../tests/browser/README.md)
- [Django isolated tests](../Django/tests/README.md): SQLite and test-only table
  setup are not the production schema provisioning mechanism.
