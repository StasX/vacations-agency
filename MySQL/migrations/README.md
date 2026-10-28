# Versioned shared-schema upgrades

Run with `docker compose run --rm database-migrations --plan` or `--apply` from
the repository root. See [the deployment and recovery guide](../../docs/database-ownership.md).

Files must be named `NNNN__description.py` with unique, ascending four-digit
versions. Each exports `upgrade(connection)` and executes explicit SQL through
the supplied MySQL connection. This connection holds the migration advisory lock;
do not close it or replace it. Close cursors and consume query results.

Document the expected old/new schema, compatibility, and recovery in the module
docstring. Check preconditions before altering data. Design each migration to
resume safely after partial DDL, since MySQL schema changes can commit implicitly.
Do not modify the ledger, switch databases, replay seed data, or execute unreviewed
input. Migration files are trusted executable deployment code.

Commit a new version for every change; previously recorded files are immutable.
Update `MySQL/data.sql` for new installations and add upgrade/data-preservation
tests under `tests/mysql/test_migrations.py`. Fresh databases still run `--apply`
to validate/register the version; the seed is not a migration history.
