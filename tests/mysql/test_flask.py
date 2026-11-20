from datetime import date
from pathlib import Path

import pytest
from flask import g
from mysql.connector import IntegrityError

from app import app
from logic.likes_logic import LikesLogic
from utils.dal import DAL
from utils.auth_token import COOKIE, get_claims, issue_token
from utils.security import Security


def sign_in(client, user_id, role=1):
    from utils.auth_status import get_status

    dal = DAL()
    try:
        account = dal.get_scalar('SELECT password FROM users WHERE id=%s', (user_id,))
        with app.app_context():
            token = issue_token({**account, 'id': user_id, 'role': role}, get_status(user_id))
        client.set_cookie(COOKIE, token)
    finally:
        dal.close()


@pytest.fixture
def client(tmp_path):
    app.config.update(TESTING=True, CSRF_ENABLED=True)
    original_root = app.root_path
    # Keep the production templates available while isolating uploaded files.
    original_folder = app.template_folder
    app.template_folder = str(Path(original_root) / original_folder)
    app.root_path = str(tmp_path)
    (tmp_path / 'static/images/vacations').mkdir(parents=True)
    try:
        yield app.test_client()
    finally:
        app.root_path = original_root
        app.template_folder = original_folder


@pytest.fixture
def admin(sql):
    sql.execute('INSERT INTO users (first_name,last_name,email,password,role_id) VALUES (%s,%s,%s,%s,%s)',
                ('Test', 'Admin', 'admin@test.example', Security.hash('Password123!'), 1))
    from utils.auth_status import get_redis
    from uuid import uuid4
    user_id = sql.lastrowid
    key = f'vacations:auth:status:{user_id}'
    get_redis().set(key, 'enabled:' + str(uuid4()))
    try:
        yield user_id
    finally:
        get_redis().delete(key)


@pytest.fixture
def trip(sql):
    sql.execute('INSERT INTO vacations (country_id,description,start_date,end_date,price,image) VALUES (%s,%s,%s,%s,%s,%s)',
                (1, 'MySQL holiday', '2099-01-01', '2099-01-02', '123.45', 'old.jpg'))
    return sql.lastrowid


def test_real_driver_round_trips_dates_prices_and_parameterized_values(sql):
    dal = DAL()
    try:
        trip_id = dal.insert('INSERT INTO vacations (country_id,description,start_date,end_date,price,image) VALUES (%s,%s,%s,%s,%s,%s)',
            (1, "O'Connor; SELECT 1", '2099-01-01', '2099-01-02', '123.45', 'trip.jpg'))
        row = dal.get_scalar('SELECT * FROM vacations WHERE id=%s', (trip_id,))
        assert row['description'] == "O'Connor; SELECT 1"
        assert row['start_date'] == date(2099, 1, 1)
        assert row['price'] == pytest.approx(123.45, abs=0.01)
    finally:
        dal.close()


@pytest.mark.parametrize('fail', [False, True])
def test_real_transaction_commits_or_rolls_back_dependent_writes(sql, trip, fail):
    dal = DAL()
    try:
        try:
            with dal.transaction():
                dal.update('UPDATE vacations SET description=%s WHERE id=%s', ('Changed', trip))
                dal.update('UPDATE vacations SET price=%s WHERE id=%s', (42, trip))
                if fail:
                    raise RuntimeError('abort dependent writes')
        except RuntimeError:
            if not fail:
                raise
        sql.execute('SELECT description, price FROM vacations WHERE id=%s', (trip,))
        description, price = sql.fetchone()
        assert description == ('MySQL holiday' if fail else 'Changed')
        assert float(price) == pytest.approx(123.45 if fail else 42)
    finally:
        dal.close()


def test_real_mysql_rejects_duplicate_likes_and_toggle_removes_only_one(admin, trip, sql):
    sql.execute('INSERT INTO vacations (country_id,description,start_date,end_date,price,image) VALUES (2,%s,%s,%s,100,%s)',
                ('Another trip', '2099-01-01', '2099-01-02', 'trip.jpg'))
    second = sql.lastrowid
    with app.test_request_context():
        likes = LikesLogic()
        likes.like(admin, trip)
        likes.like(admin, second)
        with pytest.raises(IntegrityError):
            likes.dal.insert('INSERT INTO likes (user_id,vacation_id) VALUES (%s,%s)', (admin, trip))
        likes.like(admin, trip)
    sql.execute('SELECT vacation_id FROM likes WHERE user_id=%s', (admin,))
    assert sql.fetchall() == [(second,)]


def test_concurrent_like_toggles_are_serialized(admin, trip, sql):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    ready = Barrier(2)
    def toggle():
        logic = LikesLogic()
        try:
            ready.wait(timeout=10)
            logic.like(admin, trip)
        finally:
            logic.dal.close()
    with ThreadPoolExecutor(max_workers=2) as workers:
        futures = [workers.submit(toggle) for _ in range(2)]
        for future in futures:
            future.result(timeout=30)
    sql.execute('SELECT COUNT(*) FROM likes WHERE user_id=%s AND vacation_id=%s', (admin, trip))
    assert sql.fetchone()[0] == 0


@pytest.mark.parametrize('role', [1, 2])
def test_vacation_country_name_reaches_cards_from_real_mysql(client, admin, trip, sql, role):
    sql.execute('UPDATE users SET role_id=%s WHERE id=%s', (role, admin))
    sign_in(client, admin, role)
    response = client.get('/vacations')
    assert response.status_code == 200
    assert b'<span class="card-city">Greece</span>' in response.data
    assert b'alt="Greece"' in response.data


@pytest.mark.parametrize('change', ['deleted', 'demoted', 'password'])
def test_database_account_changes_revoke_flask_admin(client, admin, trip, sql, change):
    sign_in(client, admin)
    assert client.get(f'/vacations/{trip}/edit').status_code == 200
    if change == 'deleted':
        sql.execute('DELETE FROM users WHERE id=%s', (admin,))
    elif change == 'demoted':
        sql.execute('UPDATE users SET role_id=2 WHERE id=%s', (admin,))
    else:
        sql.execute('UPDATE users SET password=%s WHERE id=%s', (Security.hash('Changed123!'), admin))
    response = client.get(f'/vacations/{trip}/edit')
    assert response.status_code == 302
    assert response.location.endswith('/login')
    assert client.get_cookie(COOKIE) is None


def test_authenticated_request_closes_real_mysql_connection(client, admin):
    sign_in(client, admin)
    # Observe the actual handles during the request; do not replace the driver.
    seen = []
    def capture(sender, template, context, **extra):
        # Authentication closes its lookup immediately, before rendering.
        seen.extend(handle.connection for handle in g.get('_database_handles', [])
                    if handle.connection is not None)
    from flask import before_render_template
    with before_render_template.connected_to(capture, app):
        assert client.get('/vacations').status_code == 200
    assert seen
    assert all(not connection.is_connected() for connection in seen)


@pytest.mark.parametrize('missing', [False, True])
def test_redis_disabled_or_missing_status_blocks_flask_jwt(client, admin, missing):
    from utils.auth_status import get_redis
    store = get_redis()
    key = f'vacations:auth:status:{admin}'
    sign_in(client, admin)
    try:
        if missing:
            store.delete(key)
        else:
            store.set(key, 'disabled:integration-test')
        assert client.get('/vacations').status_code == 302
        assert client.get_cookie(COOKIE) is None
    finally:
        store.delete(key)


def test_real_mysql_edit_validation_unchanged_update_and_missing_record(client, admin, trip, sql):
    sign_in(client, admin)
    client.get(f'/vacations/{trip}/edit')
    with app.test_request_context(headers={"Cookie": f"{COOKIE}={client.get_cookie(COOKIE).value}"}):
        token = get_claims()["csrf"]
    form = {'csrf_token': token, 'country': '1', 'description': 'MySQL holiday',
            'start_date': '2099-01-01', 'end_date': '2099-01-02', 'price': '123.45'}
    assert client.post(f'/vacations/{trip}/edit', data={**form, 'price': 'bad'}).status_code == 200
    assert client.post(f'/vacations/{trip}/edit', data=form).status_code == 302
    sql.execute('SELECT price FROM vacations WHERE id=%s', (trip,))
    assert sql.fetchone()[0] == pytest.approx(123.45, abs=0.01)
    assert client.post('/vacations/999999/edit', data=form).status_code == 404
    assert client.post('/vacations/999999/delete', data={'csrf_token': token}).status_code == 404


def test_migrated_image_queue_retries_and_preserves_shared_images(client, trip, sql, monkeypatch):
    from logic.vacations_logic import VacationsLogic
    from utils.image_cleanup import process_next_image
    from utils.image_handler import ImageHandler

    sql.execute("SELECT state FROM schema_migrations WHERE version='0002'")
    assert sql.fetchone() == ('applied',)
    sql.execute(
        'INSERT INTO vacations (country_id,description,start_date,end_date,price,image) '
        'SELECT country_id,description,start_date,end_date,price,image FROM vacations WHERE id=%s',
        (trip,),
    )
    other_trip = sql.lastrowid
    image = Path(app.root_path) / 'static/images/vacations/old.jpg'
    image.write_bytes(b'old image')

    def storage_unavailable(image_name):
        raise OSError('storage unavailable')

    try:
        with app.app_context():
            logic = VacationsLogic()
            try:
                assert logic.delete_vacation(trip) == 1
                assert process_next_image(logic.dal)
                assert image.exists()
                assert logic.delete_vacation(other_trip) == 1
                with monkeypatch.context() as failure:
                    failure.setattr(ImageHandler, 'delete_image', storage_unavailable)
                    assert process_next_image(logic.dal)
                assert image.exists()
                assert not process_next_image(logic.dal)
                sql.execute("UPDATE vacation_image_cleanup SET next_attempt_at=CURRENT_TIMESTAMP WHERE image_name='old.jpg'")
                assert process_next_image(logic.dal)
                assert not image.exists()
                assert not process_next_image(logic.dal)
            finally:
                logic.close()
    finally:
        sql.execute("DELETE FROM vacation_image_cleanup WHERE image_name='old.jpg'")
