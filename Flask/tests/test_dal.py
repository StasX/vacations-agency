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


def test_connection_error_propagates(monkeypatch, capsys):
    monkeypatch.setattr("utils.dal.mysql.connector.connect",
                        MagicMock(side_effect=Error("offline")))
    with pytest.raises(Error):
        DAL()
    assert "Connection error:" in capsys.readouterr().err


def test_close(database):
    dal, connection, _ = database
    dal.close()
    connection.close.assert_called_once_with()
