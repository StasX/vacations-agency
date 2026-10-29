from datetime import datetime
import pytest
from models.client_errors import AuthError, ResourceNotFoundError, ValidationError
from models.credentials_model import CredentialsModel
from models.user_model import UserModel
from models.vacation_model import VacationModel
from utils.date_handler import DateHandler


@pytest.mark.parametrize("email,password,message", [
    (None, "valid", "Missing email."), ("a@b.co", None, "Missing password."),
    ("a@b.c", "valid", "Email length must be 6 to 100 chars."),
    ("a" * 96 + "@b.co", "valid", "Email length must be 6 to 100 chars."),
    ("a@b.co", "abc", "Password length must be 4 to 100 characters."),
    ("a@b.co", "a" * 101, "Password length must be 4 to 100 characters."),
    ("invalid.email", "valid", "Email not valid."),
])
def test_credentials_validation_messages(email, password, message):
    assert CredentialsModel(email, password).validate() == message


@pytest.mark.parametrize("email", ["a@b.co", "a" * 95 + "@b.co"])
@pytest.mark.parametrize("password", ["abcd", "a" * 100])
def test_credentials_length_boundaries(email, password):
    assert CredentialsModel(email, password).validate() is None


@pytest.mark.parametrize("field,value,message", [
    ("first_name", None, "Missing first name."), ("last_name",
                                                  None, "Missing last name."),
    ("email", None, "Missing email."), ("password", None, "Missing password."),
    ("role", None, "Missing role."),
    ("first_name", "x", "First name length should be 2-15 characters."),
    ("first_name", "x" * 16, "First name length should be 2-15 characters."),
    ("last_name", "x", "Last name length should be 2-15 characters."),
    ("last_name", "x" * 16, "Last name length should be 2-15 characters."),
    ("email", "a@b.c", "Email length must be 6 to 30 characters."),
    ("email", "a" * 26 + "@b.co", "Email length must be 6 to 30 characters."),
    ("password", "a" * 33, "Password length must be 4 to 32 characters."),
    ("email", "bad-email", "Entered invalid email."),
    ("password", "abc", "Entered too short password."), ("role",
                                                         1, "This role unacceptable"),
])
def test_user_validation_messages(field, value, message):
    values = dict(id=None, first_name="Test", last_name="User",
                  email="test@example.com", password="abcd", role=2)
    values[field] = value
    assert UserModel(**values).validate_insert() == message


@pytest.mark.parametrize("length", [2, 15])
def test_valid_user_name_boundaries(length):
    user = UserModel(None, "x" * length, "x" * length,
                     "test@example.com", "abcd", 2)
    assert user.validate_insert() is None


@pytest.mark.parametrize("email", ["a@b.co", "a" * 25 + "@b.co"])
@pytest.mark.parametrize("password", ["abcd", "a" * 32])
def test_registration_boundary_credentials_can_pass_login_validation(email, password):
    user = UserModel(None, "Test", "User", email, password, 2)
    assert user.validate_insert() is None
    assert CredentialsModel(email, password).validate() is None


@pytest.fixture
def model(monkeypatch):
    monkeypatch.setattr(DateHandler, "now", lambda: datetime(2030, 1, 1, 12))
    return VacationModel(1, "1", "Holiday", "2030-01-02", "2030-01-03", "100", object())


@pytest.mark.parametrize("method", ["validate_insert", "validate_update"])
@pytest.mark.parametrize("field,value,message", [
    ("country", None, "Country not set."), ("description", "", "Missing description."),
    ("start_date", "", "Missing start date."), ("end_date", "", "Missing end date."),
    ("price", "", "Missing price."), ("country", "abc", "Country is invalid"),
    ("end_date", "2029-01-01", "Start of vacation can't be before vacation end"),
    ("price", "-0.01", "Price is invalid."), ("price",
                                              "10000.01", "Price is invalid."),
    ("price", "nan", "Price is invalid."), ("price", "inf", "Price is invalid."),
])
def test_vacation_validation_rules(model, method, field, value, message):
    setattr(model, field, value)
    assert getattr(model, method)() == message


@pytest.mark.parametrize("method", ["validate_insert", "validate_update"])
@pytest.mark.parametrize("price", ["0", "0.01", "9999.99", "10000"])
def test_valid_vacation_price_limits(model, method, price):
    model.price = price
    assert getattr(model, method)() is None


def test_same_day_vacation_is_allowed(model):
    model.end_date = model.start_date
    assert model.validate_insert() is None


@pytest.mark.parametrize("start", ["2029-12-31", "2030-01-01"])
def test_insert_rejects_today_and_past(model, start):
    model.start_date = start
    assert model.validate_insert() == "Start of vacation should be in future"


def test_insert_rejects_missing_image_and_non_string_country(model):
    model.image = None
    assert model.validate_insert() == "Missing image."
    model.image = object()
    model.country = 1
    assert model.validate_insert() == "Country is invalid"


@pytest.mark.parametrize("field,value", [
    ("start_date", "bad"), ("start_date", 123),
    ("end_date", "2030-02-30"), ("end_date", []),
    ("price", "bad"), ("price", "NaN"), ("price", "sNaN"),
    ("price", "Infinity"), ("price", "-Infinity"),
    ("price", "1e10000"), ("price", "10000.0000000000001"),
])
@pytest.mark.parametrize('method', ['validate_insert', 'validate_update'])
def test_malformed_values_return_error(model, method, field, value):
    setattr(model, field, value)
    assert getattr(model, method)()


def test_client_errors_retain_message_and_model():
    model = object()
    for error in (ValidationError("invalid", model), AuthError("invalid", model)):
        assert str(error) == error.message == "invalid"
        assert error.model is model
    assert AuthError("anonymous").model is None
    error = ResourceNotFoundError(17)
    assert error.id == 17
    assert str(error) == "id 17 not found."
