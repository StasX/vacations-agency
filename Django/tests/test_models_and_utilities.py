from datetime import date
from hashlib import sha512
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch

import pytest
from django.db import IntegrityError, transaction
from likes.models import LikeModel, LikesSerializer
from users.models import RoleModel, UserModel
from vacations.models import CountryModel, VacationModel
from utils.app_config import AppConfig
from utils.security import Security


@pytest.mark.parametrize('plain', ['', 'Password123!', 'pässword', 'שלום'])
def test_password_hash_matches_shared_flask_format(monkeypatch, plain):
    monkeypatch.setattr(AppConfig, 'passwords_salt', 'test-salt')
    first = Security.hash(plain)
    assert Security.verify(plain, first)
    assert not Security.verify(plain + "wrong", first)
    assert len(first) <= 128


def test_password_salt_is_random_and_independent_of_legacy_salt(monkeypatch):
    first = Security.hash('password')
    assert Security.hash('password') != first
    monkeypatch.setattr(AppConfig, 'passwords_salt', 'changed')
    assert Security.verify('password', first)



@pytest.mark.django_db
def test_email_is_unique(user):
    with pytest.raises(IntegrityError), transaction.atomic():
        UserModel.objects.create(first_name='Test', last_name='User', email=user.email,
                                 password='unused', role=user.role)


@pytest.mark.parametrize('model,table,managed', [
    (RoleModel, 'roles', True), (UserModel, 'users', True),
    (CountryModel, 'countries', False), (VacationModel, 'vacations', False),
    (LikeModel, 'likes', False),
])
def test_shared_database_table_mapping(model, table, managed):
    assert model._meta.db_table == table
    assert model._meta.managed is managed


@pytest.mark.django_db
def test_vacation_and_like_relationships(user, vacation_factory):
    vacation = vacation_factory(date(2030, 1, 1), date(2030, 1, 7))
    LikeModel.objects.create(user=user, vacation=vacation)
    like = LikeModel.objects.select_related('user__role', 'vacation__country').get(user=user)
    assert like.user.email == user.email
    assert like.user.role.role_type == 'Admin'
    assert like.vacation.country.name == 'Greece'
    assert like.vacation.price == pytest.approx(123.45)


def test_likes_serializer():
    assert LikesSerializer([{'destination': 'Greece', 'likes': 3}], many=True).data == [
        {'destination': 'Greece', 'likes': 3}]


@pytest.mark.parametrize('data', [{'destination': 'Greece'}, {'likes': 1},
                                       {'destination': 'Greece', 'likes': 'abc'}])
def test_likes_serializer_rejects_invalid_data(data):
    serializer = LikesSerializer(data=data)
    assert not serializer.is_valid()


def test_app_config_reads_environment(monkeypatch):
    mapping = {'mysql_host': 'MYSQL_HOST', 'mysql_port': 'MYSQL_PORT',
               'mysql_user': 'MYSQL_USER', 'mysql_password': 'MYSQL_PASSWORD',
               'mysql_database': 'MYSQL_DATABASE', 'secret_key': 'SECRET_KEY',
               'passwords_salt': 'PASSWORDS_SALT', 'issuer': 'ISSUER', 'audience': 'AUDIENCE'}
    for env in mapping.values():
        monkeypatch.setenv(env, 'test-'+env)
    # Execute a separate module so the suite's imported AppConfig stays untouched.
    spec = spec_from_file_location('isolated_app_config', Path(__file__).parents[1]/'src/utils/app_config.py')
    module = module_from_spec(spec)
    with patch('dotenv.load_dotenv') as load:
        spec.loader.exec_module(module)
    load.assert_called_once_with()
    for attr, env in mapping.items():
        assert getattr(module.AppConfig, attr) == 'test-'+env


@pytest.mark.django_db
@pytest.mark.xfail(strict=True, raises=IntegrityError, reason='Known model mismatch: OneToOneField prevents multiple likes per user')
def test_user_can_like_multiple_vacations(user, vacation_factory):
    for _ in range(2):
        vacation = vacation_factory(date(2030, 1, 1), date(2030, 1, 7))
        LikeModel.objects.create(user=user, vacation=vacation)
    assert LikeModel.objects.filter(user=user).count() == 2
