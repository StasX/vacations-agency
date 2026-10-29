import pytest
from redis.exceptions import ConnectionError


@pytest.mark.parametrize('path', ['/', '/login'])
def test_login_aliases_block_before_database_access(client, app, no_redis, path):
    no_redis.eval.return_value = 45
    response = client.post(path, data={'email': 'test@example.com', 'password': 'Abc123'},
                           headers={'X-Forwarded-For': '192.0.2.1'})
    assert response.status_code == 429
    assert response.headers['Retry-After'] == '45'
    assert b'Too many login attempts' in response.data
    app.test_dal.get_scalar.assert_not_called()


def test_login_get_does_not_consume_budget(client, no_redis):
    assert client.get('/login').status_code == 200
    no_redis.eval.assert_not_called()


def test_login_limiter_outage_fails_closed(client, app, no_redis):
    no_redis.eval.side_effect = ConnectionError('offline')
    response = client.post('/login', data={'email': 'test@example.com', 'password': 'Abc123'})
    assert response.status_code == 503
    app.test_dal.get_scalar.assert_not_called()
