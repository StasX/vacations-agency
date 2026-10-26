import pytest
from mysql.connector import Error

from utils.dal import DAL, close_request_connections


@pytest.mark.parametrize('path,method,data', [
    ('/vacations', 'get', None),
    ('/vacations/add', 'get', None),
    ('/vacations/12/edit', 'post', {'country': '1', 'description': ''}),
    ('/login', 'post', {'email': 'bad', 'password': ''}),
])
def test_request_closes_all_handles_on_success_and_validation(
        client, request_connections, sign_in, path, method, data):
    sign_in(1)
    response = getattr(client, method)(path, data=data)
    assert response.status_code == 200
    assert request_connections
    for connection in request_connections:
        connection.close.assert_called_once_with()


def test_authorization_redirect_closes_connection(client, request_connections):
    assert client.get('/vacations').status_code == 302
    assert len(request_connections) == 1
    request_connections[0].close.assert_called_once_with()


def test_query_failure_still_closes_connection(app, request_connections):
    with pytest.raises(Error, match='query failed'):
        with app.test_request_context():
            dal = DAL()
            request_connections[0].cursor.return_value.execute.side_effect = Error('query failed')
            dal.get_table('SELECT 1')
    request_connections[0].cursor.return_value.close.assert_called_once_with()
    request_connections[0].close.assert_called_once_with()


def test_cleanup_failure_is_logged_and_other_connections_close(app, request_connections, caplog):
    with app.test_request_context():
        DAL()
        DAL()
        request_connections[0].close.side_effect = Error('close failed')
    request_connections[1].close.assert_called_once_with()
    assert 'Failed to close request database connection' in caplog.text


def test_explicit_close_and_repeated_teardown_are_idempotent(app, request_connections):
    with app.test_request_context():
        dal = DAL()
        dal.close()
        dal.close()
        close_request_connections()
        close_request_connections()
    request_connections[0].close.assert_called_once_with()


def test_reconnect_closes_old_connection_and_teardown_closes_replacement(app, request_connections):
    with app.test_request_context():
        dal = DAL()
        request_connections[0].is_connected.return_value = False
        assert dal.get_table('SELECT 1') == []
        request_connections[0].close.assert_called_once_with()
    assert len(request_connections) == 2
    request_connections[1].close.assert_called_once_with()


def test_successive_requests_have_independent_connections(client, request_connections, sign_in):
    sign_in()
    assert client.get('/vacations').status_code == 200
    first_count = len(request_connections)
    assert client.get('/vacations').status_code == 200
    assert len(request_connections) == first_count * 2
    for connection in request_connections:
        connection.close.assert_called_once_with()


def test_public_get_opens_no_database_connection(client, request_connections):
    assert client.get('/login').status_code == 200
    assert request_connections == []
