"""Widen legacy users.password columns without changing accounts or seed data.

Restartable after interruption: a column already at least 128 chars is retained.
Recovery: keep the wider column when rolling application code back. Shrinking
would truncate modern password hashes; restore a backup only if data recovery is
required. This migration does not provision Redis account statuses.
"""
import re


def upgrade(connection):
    cursor = connection.cursor()
    try:
        cursor.execute('SELECT table_name FROM information_schema.tables '
                       'WHERE table_schema=DATABASE()')
        tables = {row[0] for row in cursor.fetchall()}
        if not {'users', 'roles', 'countries', 'vacations', 'likes'} <= tables:
            raise RuntimeError('Expected existing shared domain tables; initialize a new database with data.sql first')
        cursor.execute('SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, '
                       'COLUMN_DEFAULT, EXTRA, CHARACTER_SET_NAME, COLLATION_NAME '
                       'FROM information_schema.columns '
                       "WHERE table_schema=DATABASE() AND table_name='users' AND column_name='password'")
        column = cursor.fetchone()
        if not column or column[0] != 'varchar' or column[2] != 'NO':
            raise RuntimeError('Expected users.password to be a non-null VARCHAR; review schema before upgrading')
        if column[1] < 128:
            if column[3] is not None or column[4]:
                raise RuntimeError('Custom password default/attributes require a reviewed migration')
            charset, collation = column[5:7]
            if not all(isinstance(value, str) and re.fullmatch(r'[a-zA-Z0-9_]+', value)
                       for value in (charset, collation)):
                raise RuntimeError('Unsupported password character set or collation')
            cursor.execute('ALTER TABLE users MODIFY COLUMN password VARCHAR(128) '
                           f'CHARACTER SET {charset} COLLATE {collation} NOT NULL')
    finally:
        cursor.close()
