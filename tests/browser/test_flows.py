import re
from base64 import b64decode
from datetime import date

import pytest
from playwright.sync_api import expect


def test_customer_register_login_like_and_logout(page, seeded_database):
    page.goto('http://catalog:5000/register')
    page.get_by_label('first name', exact=True).fill('New')
    page.get_by_label('last name', exact=True).fill('Customer')
    page.get_by_label('email', exact=True).fill('new@browser.com')
    page.get_by_label('Password', exact=True).fill('Password123!')
    page.get_by_role('button', name='Register', exact=True).click()
    expect(page).to_have_url('http://catalog:5000/vacations')
    card = page.locator('.card').filter(has_text='Browser test holiday')
    expect(card.locator('.counter')).to_have_text('1')
    card.get_by_role('button', name=re.compile('Likes')).click()
    expect(card.locator('.counter')).to_have_text('2')
    seeded_database.execute('SELECT COUNT(*) FROM likes WHERE vacation_id=1')
    assert seeded_database.fetchone()[0] == 2
    page.reload()
    expect(card.locator('.counter')).to_have_text('2')
    card.get_by_role('button', name=re.compile('Likes')).click()
    expect(card.locator('.counter')).to_have_text('1')
    seeded_database.execute('SELECT COUNT(*) FROM likes WHERE vacation_id=1')
    assert seeded_database.fetchone()[0] == 1
    page.get_by_role('button', name='Logout', exact=True).click()
    page.get_by_label('email', exact=True).fill('new@browser.com')
    page.get_by_label('Password', exact=True).fill('Password123!')
    page.get_by_role('button', name='Login', exact=True).click()
    expect(page).to_have_url('http://catalog:5000/vacations')
    expect(page.get_by_text('Browser test holiday', exact=True)).to_be_visible()
    page.get_by_role('button', name='Logout', exact=True).click()
    page.goto('http://catalog:5000/vacations')
    expect(page).to_have_url('http://catalog:5000/login')


def test_administrator_add_and_update_vacation(page, seeded_database):
    page.goto('http://catalog:5000/login')
    page.get_by_label('email', exact=True).fill('admin@browser.com')
    page.get_by_label('Password', exact=True).fill('Password123!')
    page.get_by_role('button', name='Login', exact=True).click()
    page.get_by_role('link', name='Add Vacation', exact=True).click()
    page.get_by_role('button', name='Select country', exact=True).click()
    page.locator('.countries-list li').filter(has_text='Greece').click()
    page.get_by_label('description', exact=True).fill('New administrator holiday')
    page.get_by_label('start on', exact=True).fill('2099-02-01')
    page.get_by_label('end on', exact=True).fill('2099-02-07')
    page.get_by_role('spinbutton', name='Price', exact=True).fill('456.78')
    page.get_by_label('cover image', exact=True).set_input_files({
        'name': 'holiday.png', 'mimeType': 'image/png',
        'buffer': b64decode('iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAEklEQVR4nGNkYPjPwMDAxAAGAAsfAQMU4wsAAAAAAElFTkSuQmCC'),
    })
    page.get_by_role('button', name='Add Vacation', exact=True).click()
    expect(page).to_have_url('http://catalog:5000/vacations')
    card = page.locator('.card').filter(has_text='New administrator holiday')
    expect(card.locator('.card-city')).to_have_text('Greece')
    expect(card.get_by_role('button', name='$456.78', exact=True)).to_be_visible()
    expect(card.locator('img')).to_have_js_property('naturalWidth', 2)
    seeded_database.execute(
        'SELECT id,country_id,start_date,end_date,price,image FROM vacations WHERE description=%s',
        ('New administrator holiday',))
    vacation_id, country_id, start, end, price, image = seeded_database.fetchone()
    assert (country_id, start, end) == (1, date(2099, 2, 1), date(2099, 2, 7))
    assert price == pytest.approx(456.78, abs=0.01)
    assert image.endswith('.png')

    # Open the persisted vacation through its own edit link and retain its image.
    page.reload()
    card.get_by_role('link', name='Edit', exact=True).click()
    expect(page).to_have_url(f'http://catalog:5000/vacations/{vacation_id}/edit')
    expect(page.get_by_label('description', exact=True)).to_have_value('New administrator holiday')
    page.get_by_role('button', name='Greece', exact=True).click()
    page.locator('.countries-list li').filter(has_text='Italy').click()
    page.get_by_label('description', exact=True).fill('Updated administrator holiday')
    page.get_by_label('start on', exact=True).fill('2099-03-02')
    page.get_by_label('end on', exact=True).fill('2099-03-09')
    page.get_by_role('spinbutton', name='Price', exact=True).fill('789.12')
    page.get_by_role('button', name='Update Vacation', exact=True).click()
    expect(page).to_have_url('http://catalog:5000/vacations')
    page.reload()
    updated = page.locator('.card').filter(has_text='Updated administrator holiday')
    expect(updated.locator('.card-city')).to_have_text('Italy')
    expect(updated.get_by_role('button', name='$789.12', exact=True)).to_be_visible()
    expect(updated.locator('img')).to_have_js_property('naturalWidth', 2)
    expect(page.get_by_text('New administrator holiday', exact=True)).to_have_count(0)
    seeded_database.execute(
        'SELECT country_id,description,start_date,end_date,price,image FROM vacations WHERE id=%s',
        (vacation_id,))
    country_id, description, start, end, price, updated_image = seeded_database.fetchone()
    assert (country_id, description, start, end) == (
        2, 'Updated administrator holiday', date(2099, 3, 2), date(2099, 3, 9))
    assert price == pytest.approx(789.12, abs=0.01)
    assert updated_image == image


def test_administrator_login_statistics_reload_and_logout(page, seeded_database):
    page.goto('http://dashboard:3000/login')
    page.get_by_label('Email Address').fill('admin@browser.com')
    # MUI includes its required-field asterisk in the label text.
    page.get_by_label(re.compile(r'^Password\s*\*?$')).fill('Password123!')
    with page.expect_response('**/api/auth/login') as login:
        page.get_by_role('button', name='Sign In', exact=True).click()
    assert login.value.status == 200
    expect(page).to_have_url('http://dashboard:3000/home')
    endpoints = ['/api/users/total', '/api/likes/total',
                 '/api/vacations/statistics', '/api/likes/statistics']
    responses = []
    page.on('response', lambda response: responses.append(response)
            if any(response.url.endswith(path) for path in endpoints) else None)
    page.get_by_role('button', name='Statistics', exact=True).click()

    def assert_statistics():
        for label, value in [('Members count:', '2'), ('Likes count:', '1')]:
            card = page.locator('.MuiCardContent-root').filter(has_text=label)
            expect(card.locator('p')).to_have_text(value)
        expect(page.get_by_text('Greece (1)', exact=True)).to_be_visible()
        expect(page.get_by_text('Future vacations. (1)', exact=True)).to_be_visible()

    assert_statistics()
    assert {response.url.split(':3000')[1] for response in responses} == set(endpoints)
    assert all(response.status == 200 for response in responses)
    page.reload()
    assert_statistics()
    with page.expect_response('**/api/auth/logout') as logout:
        page.get_by_text('Logout', exact=True).click()
    assert logout.value.status == 204
    expect(page).to_have_url('http://dashboard:3000/login')
    assert page.evaluate("localStorage.getItem('token')") is None
    assert not any(cookie['name'] == 'refresh' for cookie in page.context.cookies())
    page.goto('http://dashboard:3000/statistics')
    expect(page).to_have_url('http://dashboard:3000/login')
