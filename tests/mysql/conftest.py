"""Real MySQL tests, isolated from both applications' mock/SQLite fixtures."""
import os
from pathlib import Path
import sys

import pytest

# Refuse cleanup unless running against the dedicated Compose test service.
if (os.environ.get('MYSQL_INTEGRATION_TESTS') != '1'
        or os.environ.get('MYSQL_HOST') != 'mysql'
        or os.environ.get('MYSQL_DATABASE') != 'vacation_agency'
        or os.environ.get('MYSQL_USER') != 'integration'):
    raise RuntimeError('Run MySQL integration tests using compose.mysql-tests.yml')

application = os.environ['TEST_APPLICATION']
if application not in ('Django', 'Flask'):
    raise RuntimeError('Unknown test application')
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / application / 'src'))

if application == 'Django':
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.settings'
    import django
    django.setup()


@pytest.fixture
def sql():
    if application == 'Django':
        import MySQLdb
        database = MySQLdb.connect(host='mysql', user='integration',
            passwd=os.environ['MYSQL_PASSWORD'], db='vacation_agency', charset='utf8mb4')
        database.autocommit(True)
        cursor = database.cursor()
    else:
        from utils.dal import DAL
        database = DAL()
        cursor = database.connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()
        database.close()


@pytest.fixture(autouse=True)
def clean_test_database(sql):
    # This database lives only in the test Compose project, with no host port.
    for table in ('likes', 'vacations', 'users', 'countries', 'roles'):
        sql.execute(f'DELETE FROM {table}')
    sql.execute("INSERT INTO roles (id, role_type) VALUES (1, 'Admin'), (2, 'User')")
    sql.execute("INSERT INTO countries (id, name) VALUES (1, 'Greece'), (2, 'Italy')")
    yield
    for table in ('likes', 'vacations', 'users', 'countries', 'roles'):
        sql.execute(f'DELETE FROM {table}')
