from datetime import datetime, timedelta, timezone

import jwt
import pytest
from django.db import connection

from users.models import RoleModel, UserModel
from vacations.models import CountryModel, VacationModel
from likes.models import LikeModel
from utils.app_config import AppConfig
from utils.security import Security


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    # Django intentionally skips these externally owned tables during migrations.
    with django_db_blocker.unblock(), connection.schema_editor() as editor:
        for model in (CountryModel, VacationModel, LikeModel):
            editor.create_model(model)


@pytest.fixture
def token_factory():
    def make(**claims):
        now = datetime.now(timezone.utc)
        payload = dict(type='access', user={'id': 1, 'role': 'Admin'},
                       exp=now + timedelta(minutes=10), iat=now,
                       iss=AppConfig.issuer, aud=AppConfig.audience, jti='test-id')
        payload.update(claims)
        return jwt.encode(payload, AppConfig.secret_key, algorithm='HS256')
    return make


@pytest.fixture
def authorized_client(client, token_factory):
    client.defaults['HTTP_AUTHORIZATION'] = token_factory()
    return client


@pytest.fixture
def user(db):
    role = RoleModel.objects.create(role_type='Admin')
    return UserModel.objects.create(first_name='Test', last_name='Admin',
                                   email='admin@example.com',
                                   password=Security.hash('Password123!'), role=role)


@pytest.fixture
def vacation_factory(db):
    def make(start, end, country='Greece'):
        destination, _ = CountryModel.objects.get_or_create(name=country)
        return VacationModel.objects.create(country=destination, description='Trip',
                                            start_date=start, end_date=end,
                                            price=123.45, image='trip.jpg')
    return make
