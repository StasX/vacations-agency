"""Enable existing MySQL users with missing Redis status; no application imports."""
import os
from uuid import uuid4


def initialize_accounts(database, redis):
    created = 0
    with database.cursor() as cursor:
        cursor.execute('SELECT id FROM users')
        for (user_id,) in cursor:
            created += bool(redis.set(f'vacations:auth:status:{user_id}',
                                      'enabled:' + str(uuid4()), nx=True))
    return created


def main():
    import mysql.connector
    from redis import Redis
    from redis.backoff import NoBackoff
    from redis.retry import Retry

    with mysql.connector.connect(
        host=os.environ['MYSQL_HOST'],
        port=int(os.environ.get('MYSQL_PORT', '3306')),
        user=os.environ['MYSQL_USER'],
        password=os.environ['MYSQL_PASSWORD'],
        database=os.environ['MYSQL_DATABASE'],
        connection_timeout=30,
    ) as database, Redis.from_url(
        os.environ['JWT_REDIS_URL'],
        password=os.environ['JWT_REDIS_PASSWORD'],
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
        retry=Retry(NoBackoff(), 0),
    ) as redis:
        created = initialize_accounts(database, redis)
    print(f'Initialized {created} account status entries.')


if __name__ == '__main__':
    main()
