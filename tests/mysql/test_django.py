from datetime import date

import pytest
from django.db import IntegrityError, connection, transaction
from django.test import Client

from likes.models import LikeModel
from users.models import UserModel
from utils.security import Security
from vacations.models import VacationModel


@pytest.fixture
def user():
    return UserModel.objects.create(first_name='Test', last_name='Admin',
                                    email='admin@test.example',
                                    password=Security.hash('Password123!'), role_id=1)


@pytest.fixture
def vacations():
    return [VacationModel.objects.create(country_id=country, description='MySQL trip',
            start_date=date(2099, 1, 1), end_date=date(2099, 1, 2),
            price=123.45, image='trip.jpg') for country in (1, 1, 2)]


def test_real_mysql_schema_has_composite_like_primary_key(sql):
    assert connection.vendor == 'mysql'
    sql.execute('SHOW INDEX FROM likes WHERE Key_name = %s', ('PRIMARY',))
    assert [row[4] for row in sql.fetchall()] == ['user_id', 'vacation_id']
    sql.execute('SELECT @@version, @@sql_mode')
    version, mode = sql.fetchone()
    assert version
    assert 'STRICT_TRANS_TABLES' in mode


def test_multiple_likes_and_duplicate_pair_constraint(user, vacations):
    for vacation in vacations:
        LikeModel.objects.create(user=user, vacation=vacation)
    with pytest.raises(IntegrityError), transaction.atomic():
        LikeModel.objects.create(user=user, vacation=vacations[0])
    LikeModel.objects.get(pk=(user.pk, vacations[0].pk)).delete()
    assert LikeModel.objects.filter(user=user).count() == 2


def test_mysql_email_collation_and_uniqueness(user):
    # The deployed utf8_general_ci schema is case-insensitive; SQLite isn't.
    with pytest.raises(IntegrityError), transaction.atomic():
        UserModel.objects.create(first_name='Other', last_name='Admin',
            email=user.email.upper(), password='unused', role_id=1)


def test_login_refresh_and_mysql_statistics(user, vacations):
    for vacation in vacations:
        LikeModel.objects.create(user=user, vacation=vacation)
    client = Client(enforce_csrf_checks=True)
    def csrf():
        response = client.get('/api/auth/csrf', secure=True)
        return {'secure': True, 'HTTP_ORIGIN': 'https://testserver',
                'HTTP_X_CSRFTOKEN': response.json()['csrf_token']}
    response = client.post('/api/auth/login', {'email': user.email, 'password': 'Password123!'},
                           content_type='application/json', **csrf())
    assert response.status_code == 200
    original_refresh = response.cookies['refresh'].value
    response = client.post('/api/auth/refresh-token', **csrf())
    assert response.status_code == 200
    access = response.json()['access_token']
    assert client.get('/api/likes/total', HTTP_AUTHORIZATION=access).json() == {'total_likes': 3}
    response = client.get('/api/likes/statistics', HTTP_AUTHORIZATION=access)
    assert response.status_code == 200
    assert sorted(response.json(), key=lambda row: row['destination']) == [
        {'destination': 'Greece', 'likes': 2}, {'destination': 'Italy', 'likes': 1}]
    client.cookies['refresh'] = original_refresh
    assert client.post('/api/auth/refresh-token', **csrf()).status_code == 401
