import pytest

from models.credentials_model import CredentialsModel
from models.user_model import UserModel
from models.vacation_model import VacationModel


def vacation(**overrides):
    values = dict(id=1, country="1", description="Holiday", start_date="2099-01-01",
                  end_date="2099-01-02", price="100", image=object())
    values.update(overrides)
    return VacationModel(**values)


@pytest.mark.parametrize("email,password", [(None, "Abc123"), ("bad", "Abc123"), ("a@b.com", "x")])
def test_invalid_credentials(email, password):
    assert CredentialsModel(email, password).validate()


def test_valid_credentials():
    assert CredentialsModel("test@example.com", "Abc123").validate() is None


def test_registration_rejects_admin_role():
    user = UserModel(None, "Test", "User", "test@example.com", "Abc123", 1)
    assert user.validate_insert()


@pytest.mark.parametrize("price", ["0", "10000"])
def test_vacation_price_boundaries(price):
    assert vacation(price=price).validate_insert() is None


@pytest.mark.parametrize("overrides", [
    {"country": "bad"}, {"description": ""}, {"start_date": "2000-01-01"},
    {"end_date": "2098-01-01"}, {"price": "-1"}, {"price": "10001"}, {"image": None},
])
def test_invalid_vacation(overrides):
    assert vacation(**overrides).validate_insert()


def test_edit_allows_existing_past_start_date_without_new_image():
    assert vacation(start_date="2000-01-01",
                    image=None).validate_update() is None


@pytest.mark.parametrize("overrides", [{"start_date": "bad-date"}, {"price": "bad-price"}])
@pytest.mark.xfail(strict=True, raises=ValueError, reason="Malformed input raises instead of returning validation errors")
def test_malformed_vacation_returns_validation_error(overrides):
    assert vacation(**overrides).validate_insert()
