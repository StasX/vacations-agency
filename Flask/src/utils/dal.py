import mysql.connector
from utils.app_config import AppConfig

class DAL:
    def __init__(self):
        self.__connect()

    def __connect(self):
        self.connection = mysql.connector.connect(
            host=AppConfig.mysql_host, user=AppConfig.mysql_user, password=AppConfig.mysql_password, database=AppConfig.mysql_database
        )

    def get_table(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, params)
            table = cursor.fetchall()
            # Consume any remaining results (important for stored procedures)
            while cursor.nextset():
                pass
            return table

    def get_scalar(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, params)
            scalar = cursor.fetchone()
            # Consume any remaining results (important for stored procedures)
            while cursor.nextset():
                pass
            return scalar

    def insert(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            self.connection.commit()
            last_row_id = cursor.lastrowid
            # Consume any remaining results (important for stored procedures)
            while cursor.nextset():
                pass
            return last_row_id

    def update(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            self.connection.commit()
            row_count = cursor.rowcount
            # Consume any remaining results (important for stored procedures)
            while cursor.nextset():
                pass
            return row_count

    def delete(self, sql, params=None):
        if not self.connection.is_connected():
            self.__connect()
        with self.connection.cursor() as cursor:
            cursor.execute(sql, params)
            self.connection.commit()
            row_count = cursor.rowcount
            # Consume any remaining results (important for stored procedures)
            while cursor.nextset():
                pass
            return row_count

    def close(self):
        self.connection.close()
