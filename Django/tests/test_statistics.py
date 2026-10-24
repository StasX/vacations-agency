from datetime import date, timedelta
from unittest.mock import patch

import pytest
from likes.models import LikeModel
from users.models import UserModel

pytestmark = pytest.mark.django_db
ENDPOINTS = ['/api/users/total', '/api/likes/total', '/api/likes/statistics',
             '/api/vacations/statistics']


def test_empty_statistics(authorized_client):
    assert authorized_client.get(ENDPOINTS[0]).json() == {'total_users': 0}
    assert authorized_client.get(ENDPOINTS[1]).json() == {'total_likes': 0}
    assert authorized_client.get(ENDPOINTS[2]).json() == []
    assert authorized_client.get(ENDPOINTS[3]).json() == {
        'past_vacations': 0, 'on_going_vacations': 0, 'future_vacations': 0}


def test_user_count(authorized_client, user):
    UserModel.objects.create(first_name='Other', last_name='User', email='other@example.com',
                             password='unused', role=user.role)
    response = authorized_client.get('/api/users/total')
    assert response.status_code == 200
    assert response.json() == {'total_users': 2}


def test_vacation_date_boundaries(authorized_client, vacation_factory):
    today = date(2030, 5, 20)
    day = timedelta(days=1)
    for start, end in [(today-2*day, today-day), (today-day, today+day),
                       (today, today+day), (today-day, today), (today, today),
                       (today+day, today+2*day)]:
        vacation_factory(start, end)
    with patch('vacations.views.date') as clock:
        clock.today.return_value = today
        response = authorized_client.get('/api/vacations/statistics')
    assert response.status_code == 200
    assert response.json() == {'past_vacations': 1, 'on_going_vacations': 4, 'future_vacations': 1}


def test_likes_group_by_country(authorized_client, user, vacation_factory):
    today = date.today()
    trips = [vacation_factory(today, today, country) for country in ['Greece', 'Greece', 'Italy', 'Spain']]
    users = [user] + [UserModel.objects.create(first_name='Test', last_name='User',
              email=f'user{i}@example.com', password='unused', role=user.role) for i in range(3)]
    for member, trip in zip(users, [trips[0], trips[0], trips[1], trips[2]]):
        LikeModel.objects.create(user=member, vacation=trip)
    assert authorized_client.get('/api/likes/total').json() == {'total_likes': 4}
    response = authorized_client.get('/api/likes/statistics')
    assert response.status_code == 200
    assert sorted(response.json(), key=lambda row: row['destination']) == [
        {'destination': 'Greece', 'likes': 3}, {'destination': 'Italy', 'likes': 1}]


@pytest.mark.parametrize('path', ENDPOINTS)
@pytest.mark.parametrize('method', ['post', 'put', 'patch', 'delete'])
def test_statistics_only_accept_get(authorized_client, path, method):
    assert getattr(authorized_client, method)(path).status_code == 405


@pytest.mark.parametrize('path,target', [
    ('/api/users/total', 'users.views.UserModel.objects'),
    ('/api/likes/total', 'likes.views.LikeModel.objects'),
    ('/api/likes/statistics', 'likes.views.LikeModel.objects'),
])
def test_database_error_returns_500(authorized_client, path, target):
    with patch(target) as manager:
        manager.all.side_effect = RuntimeError('database unavailable')
        manager.values.side_effect = RuntimeError('database unavailable')
        response = authorized_client.get(path)
    assert response.status_code == 500
    assert 'error' in response.json()


@pytest.mark.xfail(strict=True, raises=AssertionError, reason='Known bug: vacation query failure returns HTTP 200')
def test_vacation_database_error_returns_500(authorized_client):
    with patch('vacations.views.VacationModel.objects.filter', side_effect=RuntimeError('database unavailable')):
        assert authorized_client.get('/api/vacations/statistics').status_code == 500
