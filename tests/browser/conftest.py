"""Browser tests use only the disposable Compose database; no application mocks."""
import os
from base64 import b64encode
from hashlib import pbkdf2_hmac
from uuid import uuid4

import mysql.connector
import pytest
import redis


@pytest.fixture
def seeded_database():
    if (os.environ.get('BROWSER_TESTS') != '1'
            or os.environ.get('MYSQL_HOST') != 'mysql'
            or os.environ.get('MYSQL_USER') != 'integration'
            or os.environ.get('MYSQL_DATABASE') != 'vacation_agency'):
        raise RuntimeError('Run browser tests using compose.browser-tests.yml')
    database = mysql.connector.connect(
        host='mysql', user='integration', password=os.environ['MYSQL_PASSWORD'],
        database='vacation_agency', autocommit=True)
    store = redis.Redis.from_url(os.environ['JWT_REDIS_URL'],
                                password=os.environ['JWT_REDIS_PASSWORD'], decode_responses=True)
    cursor = database.cursor()

    def reset():
        cursor.execute('SELECT id FROM users')
        status_keys = [f'vacations:auth:status:{row[0]}' for row in cursor.fetchall()]
        if status_keys:
            store.delete(*status_keys)
        for table in ('likes', 'vacations', 'users', 'countries', 'roles'):
            cursor.execute(f'DELETE FROM {table}')

    try:
        reset()
        cursor.execute("INSERT INTO roles VALUES (1, 'Admin'), (2, 'User')")
        cursor.execute("INSERT INTO countries VALUES (1, 'Greece'), (2, 'Italy')")
        salt = 'browser-tests'
        digest = b64encode(pbkdf2_hmac('sha256', b'Password123!', salt.encode(), 1_000_000)).decode()
        password = f'pbkdf2_sha256$1000000${salt}${digest}'
        for user_id, role, email in ((1, 1, 'admin@browser.com'), (2, 2, 'member@browser.com')):
            cursor.execute('INSERT INTO users (id,first_name,last_name,email,password,role_id) VALUES (%s,%s,%s,%s,%s,%s)',
                           (user_id, 'Browser', 'Tester', email, password, role))
            store.set(f'vacations:auth:status:{user_id}', 'enabled:' + str(uuid4()))
        cursor.execute("INSERT INTO vacations (id,country_id,description,start_date,end_date,price,image) VALUES (1,1,'Browser test holiday','2099-01-01','2099-01-07',123.45,'')")
        cursor.execute('INSERT INTO likes (user_id,vacation_id) VALUES (2,1)')
        yield cursor
    finally:
        reset()
        cursor.close()
        database.close()
        store.close()
