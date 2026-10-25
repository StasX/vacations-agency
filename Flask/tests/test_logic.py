from unittest.mock import MagicMock
import pytest
from logic.auth_logic import AuthLogic
from logic.countries_logic import CountriesLogic
from logic.likes_logic import LikesLogic
from logic.vacations_logic import VacationsLogic
from models.credentials_model import CredentialsModel
from models.user_model import UserModel
from models.vacation_model import VacationModel


def test_auth_insert_and_lookup_are_parameterized(app):
    logic = AuthLogic()
    user = UserModel(None, "O'Connor", "User", "x' OR 1=1 --", "hash", 2)
    app.test_dal.insert.return_value = 17
    assert logic.add_user(user) == 17
    sql, params = app.test_dal.insert.call_args.args
    assert "O'Connor" not in sql and user.email not in sql
    assert params == (user.first_name, user.last_name, user.email, "hash", 2)
    row = {"id": 17}
    app.test_dal.get_scalar.return_value = row
    assert logic.get_user(CredentialsModel(user.email, "hash")) is row
    sql, params = app.test_dal.get_scalar.call_args.args
    assert user.email not in sql
    assert params == (user.email,)
    logic.close()
    app.test_dal.close.assert_called_once_with()


@pytest.mark.parametrize("result,expected", [({"COUNT(*)": 0}, False), ({"COUNT(*)": 1}, True), (None, None)])
def test_email_lookup(app, result, expected):
    app.test_dal.get_scalar.return_value = result
    assert AuthLogic().is_email_exists("test@example.com") == expected
    assert app.test_dal.get_scalar.call_args.args[1] == ("test@example.com",)


def test_countries_returns_database_rows(app):
    app.test_dal.get_table.return_value = [{"id": 1, "name": "Italy"}]
    assert CountriesLogic().get_all_countries() == [{"id": 1, "name": "Italy"}]


@pytest.mark.parametrize("result", [None, {"cnt": 0}, {"cnt": 1}])
def test_likes_toggle_returns_result(app, result):
    app.test_dal.get_scalar.return_value = result
    app.test_dal.insert.return_value = 17
    app.test_dal.delete.return_value = 1
    exists = result and result["cnt"] > 0
    assert LikesLogic().like(7, 12) == (1 if exists else 17)
    operation = app.test_dal.delete if exists else app.test_dal.insert
    assert operation.call_args.args[1] == (7, 12)
    (app.test_dal.insert if exists else app.test_dal.delete).assert_not_called()


def test_vacation_queries_return_rows_and_bind_ids(app):
    logic = VacationsLogic()
    rows = [{"id": 12}]
    app.test_dal.get_table.return_value = rows
    assert logic.get_all_vacations(7) is rows
    assert app.test_dal.get_table.call_args.args[1] == (7,)
    app.test_dal.get_scalar.return_value = rows[0]
    assert logic.get_one_vacation(12) is rows[0]
    assert app.test_dal.get_scalar.call_args.args[1] == (12,)
    app.test_dal.get_scalar.return_value = None
    assert logic.get_one_vacation(999) is None
    logic.close()
    app.test_dal.close.assert_called_once_with()


def test_vacation_update_parameters(app, monkeypatch):
    image = object()
    vacation = VacationModel(12, "1", "O'Connor holiday",
                             "2099-01-01", "2099-01-02", "100", image)
    app.test_dal.get_scalar.return_value = {"image": "old.jpg"}
    update_image = MagicMock(return_value="new.jpg")
    monkeypatch.setattr(
        "logic.vacations_logic.ImageHandler.save_image", update_image)
    monkeypatch.setattr("logic.vacations_logic.ImageHandler.delete_image", MagicMock())
    VacationsLogic().update_vacation(vacation)
    update_image.assert_called_once_with(image)
    sql, params = app.test_dal.update.call_args.args
    assert vacation.description not in sql
    assert params == ("1", vacation.description, "2099-01-01",
                      "2099-01-02", "100", "new.jpg", 12)


def test_image_failure_prevents_database_insert(app, monkeypatch):
    monkeypatch.setattr("logic.vacations_logic.ImageHandler.save_image", MagicMock(
        side_effect=OSError("disk full")))
    with pytest.raises(OSError):
        VacationsLogic().add_vacation(VacationModel(1, "1", "Holiday",
                                                    "2099-01-01", "2099-01-02", "100", object()))
    app.test_dal.insert.assert_not_called()
