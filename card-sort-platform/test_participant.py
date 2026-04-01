"""Tests for the participant /join flow and sort page."""
import os
os.environ['SECRET_KEY']        = 'test-secret'
os.environ['DASHBOARD_PASSWORD'] = 'Lexipol123'

import pytest
from app import app
from db import init_db


@pytest.fixture
def client(tmp_path):
    app.config['TESTING'] = True
    app.config['DATABASE'] = str(tmp_path / 'test.db')
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client


class TestJoinRoute:
    def test_post_join_returns_302(self, client):
        r = client.post('/join')
        assert r.status_code == 302

    def test_post_join_redirects_to_sort(self, client):
        r = client.post('/join')
        assert '/sort/' in r.headers['Location']

    def test_post_join_token_is_8_chars(self, client):
        r = client.post('/join')
        token = r.headers['Location'].split('/sort/')[-1]
        assert len(token) == 8

    def test_each_join_creates_unique_token(self, client):
        r1 = client.post('/join')
        r2 = client.post('/join')
        token1 = r1.headers['Location'].split('/sort/')[-1]
        token2 = r2.headers['Location'].split('/sort/')[-1]
        assert token1 != token2

    def test_sort_page_loads_for_joined_token(self, client):
        r = client.post('/join')
        sort_url = r.headers['Location']
        r2 = client.get(sort_url)
        assert r2.status_code == 200
        assert b'Card Sort' in r2.data

    def test_sort_page_contains_all_20_cards(self, client):
        r = client.post('/join')
        r2 = client.get(r.headers['Location'])
        # cards_json is embedded in the page
        assert b'cards_json' in r2.data or b'"id"' in r2.data

    def test_join_does_not_require_auth(self, client):
        """POST /join must be publicly accessible (no login required)."""
        r = client.post('/join')
        # Should redirect to sort, not to login
        assert '/login' not in r.headers.get('Location', '')
        assert '/sort/' in r.headers['Location']

    def test_get_join_not_allowed(self, client):
        r = client.get('/join')
        assert r.status_code == 405
