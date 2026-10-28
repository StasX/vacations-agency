"""Explicit, locked migrations for existing shared databases (never seed data)."""
import argparse
from hashlib import sha256
import os
from pathlib import Path
import re
import runpy


MIGRATIONS = Path(__file__).with_name('migrations')
LEDGER = 'schema_migrations'


def discover(directory=MIGRATIONS):
    migrations = {}
    for path in sorted(directory.glob('*.py')):
        if not re.fullmatch(r'[0-9]{4}__[a-z0-9_]+\.py', path.name):
            raise RuntimeError(f'Invalid migration filename: {path.name}')
        version = path.name[:4]
        if version in migrations:
            raise RuntimeError(f'Duplicate migration version: {version}')
        migrations[version] = (path, sha256(path.read_bytes()).hexdigest())
    if not migrations:
        raise RuntimeError('No migrations found')
    return migrations


def history(cursor):
    cursor.execute('SELECT COUNT(*) FROM information_schema.tables '
                   'WHERE table_schema=DATABASE() AND table_name=%s', (LEDGER,))
    if not cursor.fetchone()[0]:
        return {}
    cursor.execute('SELECT version, filename, checksum, state FROM schema_migrations ORDER BY version')
    return {row[0]: row[1:] for row in cursor.fetchall()}


def validate(migrations, recorded, retry_failed=None):
    for version, (filename, checksum, state) in recorded.items():
        if version not in migrations:
            raise RuntimeError(f'Missing previously recorded migration: {version}')
        path, expected = migrations[version]
        if filename != path.name or checksum != expected:
            raise RuntimeError(f'Migration changed after recording: {version}')
        if state not in ('running', 'applied'):
            raise RuntimeError(f'Invalid migration state: {version}')
        if state != 'applied' and retry_failed != version:
            raise RuntimeError(f'Incomplete migration {version}; inspect schema and use --retry-failed {version}')
    if retry_failed is not None and (
            retry_failed not in recorded or recorded[retry_failed][2] != 'running'):
        raise RuntimeError('--retry-failed must name an incomplete recorded migration')
    completed = [version for version, row in recorded.items() if row[2] == 'applied']
    if completed and any(version < max(completed) for version in migrations
                         if version not in recorded or recorded[version][2] != 'applied'):
        raise RuntimeError('Pending migration precedes an already applied version')


def migrate(connection, *, apply=False, retry_failed=None, directory=MIGRATIONS, lock_timeout=30):
    if retry_failed and not apply:
        raise RuntimeError('--retry-failed requires --apply')
    migrations = discover(directory)
    cursor = connection.cursor()
    locked = False
    lock_name = None
    try:
        # Named locks survive MySQL DDL's implicit commits.
        cursor.execute('SELECT DATABASE()')
        database = cursor.fetchone()[0]
        if not database:
            raise RuntimeError('A target database must be selected')
        lock_name = 'vacations-migrate:' + sha256(database.encode()).hexdigest()[:40]
        cursor.execute('SELECT GET_LOCK(%s, %s)', (lock_name, lock_timeout))
        if cursor.fetchone()[0] != 1:
            raise RuntimeError('Another database migration is running')
        locked = True
        recorded = history(cursor)
        validate(migrations, recorded, retry_failed)
        pending = [version for version in migrations
                   if version not in recorded or recorded[version][2] != 'applied']
        if not apply:
            for version, (path, _) in migrations.items():
                print(f'{version} {path.name}: {"pending" if version in pending else "applied"}')
            return pending
        cursor.execute('''CREATE TABLE IF NOT EXISTS schema_migrations (
            version CHAR(4) PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            checksum CHAR(64) NOT NULL,
            state VARCHAR(16) NOT NULL,
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            applied_at TIMESTAMP NULL
        ) ENGINE=InnoDB''')
        connection.commit()
        for version in pending:
            path, checksum = migrations[version]
            if version not in recorded:
                cursor.execute('INSERT INTO schema_migrations (version,filename,checksum,state) '
                               'VALUES (%s,%s,%s,%s)', (version, path.name, checksum, 'running'))
                connection.commit()
            # Keep the running marker on failure/crash: DDL cannot be rolled back.
            upgrade = runpy.run_path(str(path))['upgrade']
            upgrade(connection)
            connection.commit()
            cursor.execute("UPDATE schema_migrations SET state='applied', applied_at=CURRENT_TIMESTAMP "
                           'WHERE version=%s', (version,))
            connection.commit()
            print(f'Applied {path.name}')
        if not pending:
            print('Database migrations are up to date')
        return pending
    finally:
        if locked:
            # Discard uncommitted DML; already committed DDL and ledger survive.
            connection.rollback()
            cursor.execute('SELECT RELEASE_LOCK(%s)', (lock_name,))
            cursor.fetchone()
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', action='store_true', help='Inspect history without writing schema or data')
    mode.add_argument('--apply', action='store_true', help='Apply pending migrations')
    parser.add_argument('--retry-failed', help='Resume a reviewed, restartable incomplete version')
    args = parser.parse_args()
    import mysql.connector
    connection = mysql.connector.connect(
        host=os.environ['MYSQL_HOST'], port=int(os.environ.get('MYSQL_PORT', '3306')),
        user=os.environ['MYSQL_USER'], password=os.environ['MYSQL_PASSWORD'],
        database=os.environ['MYSQL_DATABASE'], autocommit=True, connection_timeout=10)
    try:
        migrate(connection, apply=args.apply, retry_failed=args.retry_failed)
    finally:
        connection.close()


if __name__ == '__main__':
    main()
