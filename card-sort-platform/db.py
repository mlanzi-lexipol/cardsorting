import sqlite3
import os
from flask import g

DATABASE = os.path.join(os.path.dirname(__file__), 'data', 'card_sort.db')


def get_db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    db = sqlite3.connect(DATABASE)
    db.executescript('''
        CREATE TABLE IF NOT EXISTS sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            token           TEXT    UNIQUE NOT NULL,
            participant_name TEXT,
            role            TEXT    DEFAULT 'Multi-product Admin',
            status          TEXT    DEFAULT 'pending',
            card_order      TEXT,
            started_at      TEXT,
            completed_at    TEXT,
            duration_seconds INTEGER,
            created_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER NOT NULL,
            card_id         TEXT    NOT NULL,
            card_label      TEXT    NOT NULL,
            category        TEXT    NOT NULL,
            confidence      INTEGER,
            time_seconds    REAL,
            emotional_signal TEXT   DEFAULT 'neutral',
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );

        CREATE TABLE IF NOT EXISTS categories (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      INTEGER NOT NULL,
            name            TEXT    NOT NULL,
            is_user_created INTEGER DEFAULT 0,
            card_count      INTEGER DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    ''')
    db.commit()
    db.close()
    print(f'[DB] Initialised at {DATABASE}')
