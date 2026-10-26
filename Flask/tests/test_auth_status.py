import pytest
from redis.exceptions import ConnectionError
from utils.security import Security
from utils import auth_status


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


def test_missing_status_cannot_login_or_recreate_status(client, app, no_redis):
    app.test_dal.get_scalar.return_value = dict(id=7, password=Security.hash('Abc123'), role=1)
    no_redis.get.return_value = None
    response = client.post('/login', data={'email': 'test@example.com', 'password': 'Abc123'})
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert 'current_user' not in session
    no_redis.set.assert_not_called()


def test_missing_status_invalidates_existing_session(client, sign_in, no_redis):
    sign_in()
    no_redis.get.return_value = None
    assert client.get('/vacations').status_code == 302
    with client.session_transaction() as session:
        assert 'current_user' not in session
    no_redis.set.assert_not_called()


def test_registration_initialization_never_overwrites_disabled_status(no_redis):
    no_redis.get.return_value = 'disabled:existing-version'
    assert auth_status.initialize_status(7) == 'disabled:existing-version'
    args, kwargs = no_redis.set.call_args
    assert args[0] == 'vacations:auth:status:7'
    assert auth_status.is_enabled(args[1])
    assert kwargs == {'nx': True}


@pytest.mark.parametrize('status', [None, '', 'enabled:', 'enabled:initial', 'enabled:invalid'])
def test_missing_or_malformed_status_is_not_enabled(status):
    assert not auth_status.is_enabled(status)
