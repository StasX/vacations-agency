"""Upgrade a populated legacy schema, never by replaying the seed dump."""
import importlib.util
import os
from pathlib import Path
import shutil

import mysql.connector
import pytest

spec = importlib.util.spec_from_file_location('migration_runner', Path(__file__).resolve().parents[2] / 'MySQL/migrate.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture
def database():
    connection = mysql.connector.connect(host='mysql', user='integration',
        password=os.environ['MYSQL_PASSWORD'], database='vacation_agency', autocommit=True)
    cursor = connection.cursor()
    cursor.execute('DROP TABLE IF EXISTS schema_migrations')
    try:
        yield connection
    finally:
        cursor.execute('DROP TABLE IF EXISTS schema_migrations')
        cursor.execute('DROP TABLE IF EXISTS migration_probe')
        cursor.execute('ALTER TABLE users MODIFY COLUMN password VARCHAR(128) NOT NULL')
        cursor.close()
        connection.close()


def test_upgrade_retains_existing_accounts_and_relationships(database):
    cursor = database.cursor()
    cursor.execute('ALTER TABLE users MODIFY COLUMN password VARCHAR(64) NOT NULL')
    cursor.execute("INSERT INTO users (id,first_name,last_name,email,password,role_id) VALUES (101,'Existing','Customer','existing@test.com',%s,2)", ('a' * 64,))
    cursor.execute("INSERT INTO vacations (id,country_id,description,start_date,end_date,price,image) VALUES (101,1,'Existing holiday','2099-01-01','2099-01-07',123.45,'existing.png')")
    cursor.execute('INSERT INTO likes (user_id,vacation_id) VALUES (101,101)')
    snapshots = {}
    for table in ('users', 'roles', 'countries', 'vacations', 'likes'):
        cursor.execute(f'SELECT * FROM {table} ORDER BY 1')
        snapshots[table] = cursor.fetchall()
    assert runner.migrate(database) == ['0001']
    cursor.execute("SHOW TABLES LIKE 'schema_migrations'")
    assert cursor.fetchone() is None  # Plan creates no ledger or schema.
    assert runner.migrate(database, apply=True) == ['0001']
    assert runner.migrate(database, apply=True) == []
    for table, rows in snapshots.items():
        cursor.execute(f'SELECT * FROM {table} ORDER BY 1')
        assert cursor.fetchall() == rows
    cursor.execute("SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='users' AND column_name='password'")
    assert cursor.fetchone()[0] == 128
    cursor.execute('SELECT version,state FROM schema_migrations')
    assert cursor.fetchall() == [('0001', 'applied')]
    cursor.close()


def test_current_schema_can_be_baselined_without_seed_replay(database, tmp_path):
    assert runner.migrate(database, apply=True) == ['0001']
    assert runner.migrate(database) == []
    shutil.copytree(runner.MIGRATIONS, tmp_path / 'migrations')
    migration = next((tmp_path / 'migrations').glob('*.py'))
    migration.write_text(migration.read_text() + '\n# altered history\n')
    with pytest.raises(RuntimeError, match='changed after recording'):
        runner.migrate(database, apply=True, directory=tmp_path / 'migrations')


def test_wider_password_column_is_never_narrowed(database):
    cursor = database.cursor()
    try:
        cursor.execute('ALTER TABLE users MODIFY COLUMN password VARCHAR(255) NOT NULL')
        assert runner.migrate(database, apply=True) == ['0001']
        cursor.execute("SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='users' AND column_name='password'")
        assert cursor.fetchone()[0] == 255
    finally:
        cursor.close()


def test_interrupted_ddl_blocks_until_explicit_reviewed_retry(database, tmp_path):
    shutil.copytree(runner.MIGRATIONS, tmp_path / 'migrations')
    migration = tmp_path / 'migrations/0002__interrupted.py'
    migration.write_text('''def upgrade(connection):
    cursor = connection.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE 'migration_probe'")
        if cursor.fetchone() is None:
            cursor.execute('CREATE TABLE migration_probe (id INT PRIMARY KEY)')
            raise RuntimeError('simulated interruption after DDL')
    finally:
        cursor.close()
''')
    with pytest.raises(RuntimeError, match='simulated interruption'):
        runner.migrate(database, apply=True, directory=migration.parent)
    with pytest.raises(RuntimeError, match='Incomplete migration 0002'):
        runner.migrate(database, apply=True, directory=migration.parent)
    assert runner.migrate(database, apply=True, directory=migration.parent, retry_failed='0002') == ['0002']
    assert runner.migrate(database, apply=True, directory=migration.parent) == []


def test_concurrent_runner_cannot_apply_while_lock_is_held(database):
    from hashlib import sha256
    other = mysql.connector.connect(host='mysql', user='integration',
        password=os.environ['MYSQL_PASSWORD'], database='vacation_agency', autocommit=True)
    cursor = other.cursor()
    lock_name = 'vacations-migrate:' + sha256(b'vacation_agency').hexdigest()[:40]
    try:
        cursor.execute('SELECT GET_LOCK(%s,0)', (lock_name,))
        assert cursor.fetchone()[0] == 1
        with pytest.raises(RuntimeError, match='Another database migration'):
            runner.migrate(database, apply=True, lock_timeout=0)
    finally:
        cursor.close()
        other.close()
