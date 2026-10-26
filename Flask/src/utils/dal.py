import mysql.connector
import logging
from flask import g, has_request_context
from utils.app_config import AppConfig


def close_request_connections(error=None):
    handles = g.pop('_database_handles', [])
    for handle in handles:
        try:
            handle.close()
        except Exception:
            # Cleanup failures must not mask the response or skip other handles.
            logging.getLogger(__name__).exception('Failed to close request database connection')


class DAL:
    def __init__(self):
        self.connection = None
        self.__connect()
        if has_request_context():
            if '_database_handles' not in g:
                g._database_handles = []
            g._database_handles.append(self)

    def __connect(self):
        self.close()
        self.connection = mysql.connector.connect(
            host=AppConfig.mysql_host,
            user=AppConfig.mysql_user,
            password=AppConfig.mysql_password,
            database=AppConfig.mysql_database,
            use_unicode=True,
            charset='utf8mb4',
            autocommit=True,
            get_warnings=False,
            raise_on_warnings=False,
            connection_timeout=30
        )

    def get_table(self, sql, params=None):
        if self.connection is None or not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_scalar(self, sql, params=None):
        if self.connection is None or not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        finally:
            cursor.close()

    def insert(self, sql, params=None):
        if self.connection is None or not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.lastrowid
        finally:
            cursor.close()

    def update(self, sql, params=None):
        if self.connection is None or not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.rowcount
        finally:
            cursor.close()

    def delete(self, sql, params=None):
        if self.connection is None or not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.rowcount
        finally:
            cursor.close()

    def close(self):
        connection, self.connection = self.connection, None
        if connection is not None:
            connection.close()
