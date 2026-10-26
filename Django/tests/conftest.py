from datetime import datetime, timedelta, timezone

import jwt
import pytest
import fakeredis
from uuid import uuid4
from django.db import connection

from users.models import RoleModel, UserModel
from vacations.models import CountryModel, VacationModel
from likes.models import LikeModel
from utils.app_config import AppConfig
from utils.security import Security
from utils.tokens import password_fingerprint
from utils import refresh_tokens


@pytest.fixture(autouse=True)
def redis_store(monkeypatch):
    store = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(refresh_tokens, 'get_redis', lambda: store)
    yield store
    store.close()


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    # Django intentionally skips these externally owned tables during migrations.
    with django_db_blocker.unblock(), connection.schema_editor() as editor:
        for model in (CountryModel, VacationModel, LikeModel):
            editor.create_model(model)


@pytest.fixture
def token_factory(db):
    def make(**claims):
        now = datetime.now(timezone.utc)
        payload = dict(type='access', user={'id': 1, 'role': 'Admin'},
                       exp=now + timedelta(minutes=10), iat=now,
                       iss=AppConfig.issuer, aud=AppConfig.audience, jti='test-id')
        payload.update(claims)
        member = UserModel.objects.filter(pk=1).first()
        if payload.get('type') == 'refresh' and member:
            payload.setdefault('pwd', password_fingerprint(member))
        if payload.get('type') == 'refresh':
            payload.setdefault('sid', str(uuid4()))
        token = jwt.encode(payload, AppConfig.secret_key, algorithm='HS256')
        if payload.get('type') == 'refresh':
            try:
                refresh_tokens.register(token)
            except jwt.InvalidTokenError:
                pass
        return token
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
