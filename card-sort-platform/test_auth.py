"""Auth tests for the researcher dashboard."""
import os
import sys
import tempfile

# Point to a throwaway DB so tests don't touch production data
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['DASHBOARD_PASSWORD'] = 'Lexipol123'

import pytest
from app import app
from db import init_db


@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / 'test.db')
    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client


PROTECTED_ROUTES = [
    ('GET',  '/dashboard'),
    ('POST', '/dashboard/create-session'),
    ('POST', '/dashboard/delete-session/1'),
    ('GET',  '/api/stats'),
    ('GET',  '/api/analysis'),
    ('GET',  '/api/export/json'),
    ('GET',  '/api/export/csv'),
]


class TestUnauthenticated:
    def test_dashboard_redirects_to_login(self, client):
        r = client.get('/dashboard')
        assert r.status_code == 302
        assert '/login' in r.headers['Location']

    def test_all_protected_routes_redirect(self, client):
        for method, path in PROTECTED_ROUTES:
            if method == 'GET':
                r = client.get(path)
            else:
                r = client.post(path)
            assert r.status_code == 302, f"{method} {path} should redirect"
            assert '/login' in r.headers['Location'], f"{method} {path} should redirect to /login"


class TestLogin:
    def test_login_page_renders(self, client):
        r = client.get('/login')
        assert r.status_code == 200
        assert b'Researcher Dashboard' in r.data

    def test_wrong_password_shows_error(self, client):
        r = client.post('/login', data={'password': 'wrongpassword'})
        assert r.status_code == 200
        assert b'Incorrect password' in r.data

    def test_correct_password_redirects_to_dashboard(self, client):
        r = client.post('/login', data={'password': 'Lexipol123'})
        assert r.status_code == 302
        assert '/dashboard' in r.headers['Location']


class TestAuthenticated:
    def _login(self, client):
        client.post('/login', data={'password': 'Lexipol123'})

    def test_dashboard_accessible_after_login(self, client):
        self._login(client)
        r = client.get('/dashboard')
        assert r.status_code == 200

    def test_api_stats_accessible_after_login(self, client):
        self._login(client)
        r = client.get('/api/stats')
        assert r.status_code == 200

    def test_api_analysis_accessible_after_login(self, client):
        self._login(client)
        r = client.get('/api/analysis')
        assert r.status_code == 200


class TestLogout:
    def test_logout_clears_session_and_redirects(self, client):
        client.post('/login', data={'password': 'Lexipol123'})
        # Confirm access works before logout
        assert client.get('/dashboard').status_code == 200
        # Logout
        r = client.post('/logout')
        assert r.status_code == 302
        assert '/login' in r.headers['Location']
        # Dashboard should redirect again after logout
        r2 = client.get('/dashboard')
        assert r2.status_code == 302
        assert '/login' in r2.headers['Location']
