import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "doomstopper.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    """Initialize the database with required tables"""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table to store Telegram chat IDs and Twitter tokens
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id TEXT PRIMARY KEY,
                access_token TEXT,
                refresh_token TEXT,
                token_expires_at INTEGER,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)

        # OAuth sessions table for temporary state storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_sessions (
                state TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL,
                code_verifier TEXT NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        """)

        # Clean up old sessions (older than 1 hour)
        cursor.execute("""
            DELETE FROM oauth_sessions
            WHERE created_at < strftime('%s', 'now') - 3600
        """)

def save_user_tokens(chat_id, access_token, refresh_token=None, expires_at=None):
    """Save or update user tokens"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (chat_id, access_token, refresh_token, token_expires_at, updated_at)
            VALUES (?, ?, ?, ?, strftime('%s', 'now'))
            ON CONFLICT(chat_id) DO UPDATE SET
                access_token = excluded.access_token,
                refresh_token = excluded.refresh_token,
                token_expires_at = excluded.token_expires_at,
                updated_at = excluded.updated_at
        """, (chat_id, access_token, refresh_token, expires_at))

def get_user_token(chat_id):
    """Get user's access token"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT access_token, refresh_token, token_expires_at
            FROM users
            WHERE chat_id = ?
        """, (chat_id,))
        row = cursor.fetchone()
        if row:
            return {
                'access_token': row['access_token'],
                'refresh_token': row['refresh_token'],
                'expires_at': row['token_expires_at']
            }
        return None

def get_all_users():
    """Get all registered users"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users WHERE access_token IS NOT NULL")
        return [row['chat_id'] for row in cursor.fetchall()]

def save_oauth_session(state, chat_id, code_verifier):
    """Save OAuth session for PKCE flow"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO oauth_sessions (state, chat_id, code_verifier)
            VALUES (?, ?, ?)
        """, (state, chat_id, code_verifier))

def get_oauth_session(state):
    """Get OAuth session data"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT chat_id, code_verifier
            FROM oauth_sessions
            WHERE state = ?
        """, (state,))
        row = cursor.fetchone()
        if row:
            return {
                'chat_id': row['chat_id'],
                'code_verifier': row['code_verifier']
            }
        return None

def delete_oauth_session(state):
    """Delete OAuth session after use"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM oauth_sessions WHERE state = ?", (state,))

def user_exists(chat_id):
    """Check if user exists and has a valid token"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM users
            WHERE chat_id = ? AND access_token IS NOT NULL
        """, (chat_id,))
        return cursor.fetchone() is not None