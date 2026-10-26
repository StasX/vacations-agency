import pytest
from redis.exceptions import ConnectionError
from utils.security import Security


def test_disabled_account_cannot_login(client, app, no_redis):
    app.test_dal.get_scalar.return_value = dict(id=7, password=Security.hash('Abc123'), role=1)
    no_redis.get.return_value = 'disabled:version'
    response = client.post('/login', data={'email': 'test@example.com', 'password': 'Abc123'})
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert 'current_user' not in session


@pytest.mark.parametrize('status', ['disabled:version', 'enabled:new-version'])
@pytest.mark.parametrize('path,method', [('/vacations', 'get'), ('/likes/like/1', 'post')])
def test_status_change_invalidates_session(client, sign_in, no_redis, status, path, method):
    sign_in(role=1)
    no_redis.get.return_value = status
    response = getattr(client, method)(path)
    assert response.status_code == 302
    assert response.location.endswith('/login')
    with client.session_transaction() as session:
        assert 'current_user' not in session


def test_redis_outage_blocks_existing_session(client, sign_in, no_redis):
    sign_in()
    no_redis.get.side_effect = ConnectionError('offline')
    response = client.get('/vacations')
    assert response.status_code == 503
    assert response.headers['Retry-After'] == '5'
