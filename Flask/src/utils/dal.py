import mysql.connector
from mysql.connector import Error, errorcode
from utils.app_config import AppConfig

class DAL:
    def __init__(self):
        self.__connect()

    def __connect(self):
        try:
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
        except Error as e:
            import sys
            print(f"Connection error: {e}", file=sys.stderr)
            raise

    def get_table(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def get_scalar(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchone()
        except Error as e:
            import sys
            print(f"Database error in get_scalar: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()

    def insert(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.lastrowid
        except Error as e:
            import sys
            print(f"Database error in insert: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()

    def update(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.rowcount
        finally:
            cursor.close()

    def delete(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor.rowcount
        finally:
            cursor.close()

    def close(self):
        self.connection.close()
