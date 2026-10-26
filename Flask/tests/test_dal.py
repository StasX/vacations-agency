from unittest.mock import MagicMock

import pytest
from mysql.connector import Error

from utils.app_config import AppConfig
from utils.dal import DAL


@pytest.fixture
def database(monkeypatch):
    connection = MagicMock()
    connection.is_connected.return_value = True
    connector = MagicMock(return_value=connection)
    monkeypatch.setattr("utils.dal.mysql.connector.connect", connector)
    return DAL(), connection, connector


def test_connection_configuration(database):
    _, _, connector = database
    options = connector.call_args.kwargs
    assert options == dict(host=AppConfig.mysql_host, user=AppConfig.mysql_user,
                           password=AppConfig.mysql_password, database=AppConfig.mysql_database,
                           use_unicode=True, charset="utf8mb4", autocommit=True,
                           get_warnings=False, raise_on_warnings=False, connection_timeout=30)


@pytest.mark.parametrize("method,result_attribute,result", [
    ("get_table", "fetchall", [{"id": 1}]),
    ("get_scalar", "fetchone", {"id": 1}),
    ("insert", "lastrowid", 17), ("update",
                                  "rowcount", 2), ("delete", "rowcount", 1),
])
@pytest.mark.parametrize("connected", [True, False])
def test_query_results_parameters_cleanup_and_reconnect(database, method, result_attribute, result, connected):
    dal, connection, connector = database
    connection.is_connected.return_value = connected
    cursor = connection.cursor.return_value
    if result_attribute in ("fetchall", "fetchone"):
        getattr(cursor, result_attribute).return_value = result
    else:
        setattr(cursor, result_attribute, result)
    assert getattr(dal, method)("QUERY WHERE id=%s", (7,)) == result
    cursor.execute.assert_called_once_with("QUERY WHERE id=%s", (7,))
    cursor.close.assert_called_once_with()
    assert connector.call_count == (1 if connected else 2)
    connection.cursor.assert_called_once_with(
        **({"dictionary": True} if method.startswith("get_") else {}))


@pytest.mark.parametrize("method", ["get_table", "get_scalar", "insert", "update", "delete"])
def test_query_failure_closes_cursor_and_propagates(database, method):
    dal, connection, _ = database
    error = Error("query failed")
    connection.cursor.return_value.execute.side_effect = error
    with pytest.raises(Error) as caught:
        getattr(dal, method)("QUERY")
    assert caught.value is error
    connection.cursor.return_value.close.assert_called_once_with()


@pytest.mark.parametrize("method", ["get_table", "get_scalar"])
def test_fetch_failure_closes_cursor(database, method):
    dal, connection, _ = database
    cursor = connection.cursor.return_value
    getattr(cursor, "fetchall" if method ==
            "get_table" else "fetchone").side_effect = Error("fetch failed")
    with pytest.raises(Error):
        getattr(dal, method)("QUERY")
    cursor.close.assert_called_once_with()


def test_connection_error_propagates(monkeypatch):
    error = Error('offline')
    monkeypatch.setattr("utils.dal.mysql.connector.connect",
                        MagicMock(side_effect=error))
    with pytest.raises(Error) as caught:
        DAL()
    assert caught.value is error


def test_close(database):
    dal, connection, _ = database
    dal.close()
    connection.close.assert_called_once_with()


def test_transaction_commits_dependent_statements(database):
    dal, connection, _ = database
    with dal.transaction():
        dal.insert('INSERT FIRST')
        dal.update('UPDATE SECOND')
        connection.commit.assert_not_called()
    connection.start_transaction.assert_called_once_with()
    connection.commit.assert_called_once_with()
    connection.rollback.assert_not_called()


@pytest.mark.parametrize('failure', ['query', 'commit'])
def test_transaction_rolls_back_failure(database, failure):
    dal, connection, _ = database
    error = Error('write failed')
    if failure == 'query':
        connection.cursor.return_value.execute.side_effect = [None, error]
    else:
        connection.commit.side_effect = error
    with pytest.raises(Error) as caught:
        with dal.transaction():
            dal.insert('FIRST')
            dal.update('SECOND')
    assert caught.value is error
    connection.rollback.assert_called_once_with()
    assert not dal._in_transaction


def test_transaction_never_reconnects_after_connection_loss(database):
    dal, connection, connector = database
    with pytest.raises(Error, match='Connection lost'):
        with dal.transaction():
            dal.insert('FIRST')
            connection.is_connected.return_value = False
            dal.update('SECOND')
    assert connector.call_count == 1
    connection.commit.assert_not_called()
    connection.rollback.assert_called_once_with()


def test_nested_transaction_rolls_back_without_inner_commit(database):
    dal, connection, _ = database
    with pytest.raises(RuntimeError, match='Nested'):
        with dal.transaction():
            with dal.transaction():
                pass
    connection.start_transaction.assert_called_once_with()
    connection.commit.assert_not_called()
    connection.rollback.assert_called_once_with()


def test_like_toggle_rolls_back_when_write_fails(database):
    from logic.likes_logic import LikesLogic
    dal, connection, _ = database
    logic = LikesLogic.__new__(LikesLogic)
    logic.dal = dal
    cursor = connection.cursor.return_value
    cursor.fetchone.side_effect = [{'id': 7}, {'cnt': 0}]
    cursor.execute.side_effect = [None, None, Error('insert failed')]
    with pytest.raises(Error, match='insert failed'):
        logic.like(7, 12)
    connection.rollback.assert_called_once_with()
    connection.commit.assert_not_called()
    assert 'FOR UPDATE' in cursor.execute.call_args_list[0].args[0]
