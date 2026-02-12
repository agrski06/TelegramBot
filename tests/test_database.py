import pytest
import tempfile
import os
from unittest.mock import patch
from src.db import database


class TestDatabase:
    """Test database operations"""

    @pytest.fixture(autouse=True)
    def setup_temp_db(self):
        """Setup temporary database for each test"""
        self.fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)

        with patch('src.db.database.DB_PATH', self.path):
            database.init_db()
            yield

        # Cleanup
        try:
            os.unlink(self.path)
        except:
            pass

    def test_init_db(self):
        """Test database initialization"""
        with patch('src.db.database.DB_PATH', self.path):
            database.init_db()

            # Verify tables exist
            with database.get_db() as conn:
                cursor = conn.cursor()

                # Check users table
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='users'
                """)
                assert cursor.fetchone() is not None

                # Check oauth_sessions table
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='oauth_sessions'
                """)
                assert cursor.fetchone() is not None

    def test_save_user_tokens(self):
        """Test saving user tokens"""
        with patch('src.db.database.DB_PATH', self.path):
            chat_id = "123456"
            access_token = "test_access_token"
            refresh_token = "test_refresh_token"
            expires_at = 1234567890

            database.save_user_tokens(
                chat_id=chat_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at
            )

            # Verify token was saved
            token_data = database.get_user_token(chat_id)
            assert token_data is not None
            assert token_data['access_token'] == access_token
            assert token_data['refresh_token'] == refresh_token
            assert token_data['expires_at'] == expires_at

    def test_update_user_tokens(self):
        """Test updating existing user tokens"""
        with patch('src.db.database.DB_PATH', self.path):
            chat_id = "123456"

            # Save initial tokens
            database.save_user_tokens(
                chat_id=chat_id,
                access_token="old_token",
                refresh_token="old_refresh"
            )

            # Update tokens
            database.save_user_tokens(
                chat_id=chat_id,
                access_token="new_token",
                refresh_token="new_refresh"
            )

            # Verify tokens were updated
            token_data = database.get_user_token(chat_id)
            assert token_data['access_token'] == "new_token"
            assert token_data['refresh_token'] == "new_refresh"

    def test_get_user_token_not_found(self):
        """Test getting token for non-existent user"""
        with patch('src.db.database.DB_PATH', self.path):
            token_data = database.get_user_token("nonexistent")
            assert token_data is None

    def test_save_oauth_session(self):
        """Test saving OAuth session"""
        with patch('src.db.database.DB_PATH', self.path):
            state = "test_state_123"
            chat_id = "123456"
            code_verifier = "test_code_verifier"

            database.save_oauth_session(state, chat_id, code_verifier)

            # Verify session was saved
            session = database.get_oauth_session(state)
            assert session is not None
            assert session['chat_id'] == chat_id
            assert session['code_verifier'] == code_verifier

    def test_get_oauth_session_not_found(self):
        """Test getting non-existent OAuth session"""
        with patch('src.db.database.DB_PATH', self.path):
            session = database.get_oauth_session("nonexistent")
            assert session is None

    def test_delete_oauth_session(self):
        """Test deleting OAuth session"""
        with patch('src.db.database.DB_PATH', self.path):
            state = "test_state_123"
            chat_id = "123456"
            code_verifier = "test_code_verifier"

            # Save session
            database.save_oauth_session(state, chat_id, code_verifier)

            # Verify it exists
            session = database.get_oauth_session(state)
            assert session is not None

            # Delete session
            database.delete_oauth_session(state)

            # Verify it's deleted
            session = database.get_oauth_session(state)
            assert session is None

    def test_user_exists(self):
        """Test checking if user exists"""
        with patch('src.db.database.DB_PATH', self.path):
            chat_id = "123456"

            # User doesn't exist yet
            assert database.user_exists(chat_id) is False

            # Save user tokens
            database.save_user_tokens(
                chat_id=chat_id,
                access_token="test_token"
            )

            # User should now exist
            assert database.user_exists(chat_id) is True

    def test_get_all_users(self):
        """Test getting all registered users"""
        with patch('src.db.database.DB_PATH', self.path):
            # No users initially
            users = database.get_all_users()
            assert len(users) == 0

            # Add multiple users
            database.save_user_tokens("user1", "token1")
            database.save_user_tokens("user2", "token2")
            database.save_user_tokens("user3", "token3")

            # Get all users
            users = database.get_all_users()
            assert len(users) == 3
            assert "user1" in users
            assert "user2" in users
            assert "user3" in users

    def test_get_all_users_excludes_no_token(self):
        """Test that get_all_users excludes users without tokens"""
        with patch('src.db.database.DB_PATH', self.path):
            # Add user with token
            database.save_user_tokens("user_with_token", "token")

            # Add user without token (by manually inserting)
            with database.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (chat_id, access_token) VALUES (?, ?)",
                    ("user_without_token", None)
                )

            # Only user with token should be returned
            users = database.get_all_users()
            assert len(users) == 1
            assert "user_with_token" in users
            assert "user_without_token" not in users

    def test_oauth_session_cleanup(self):
        """Test that old OAuth sessions are cleaned up on init"""
        with patch('src.db.database.DB_PATH', self.path):
            # Manually insert an old session
            with database.get_db() as conn:
                cursor = conn.cursor()
                # Insert session with old timestamp (2 hours ago)
                old_timestamp = 1000000000
                cursor.execute(
                    """INSERT INTO oauth_sessions
                       (state, chat_id, code_verifier, created_at)
                       VALUES (?, ?, ?, ?)""",
                    ("old_state", "123", "verifier", old_timestamp)
                )

            # Re-initialize database (should clean up old sessions)
            database.init_db()

            # Old session should be gone
            session = database.get_oauth_session("old_state")
            assert session is None

    def test_context_manager_commit(self):
        """Test that database context manager commits changes"""
        with patch('src.db.database.DB_PATH', self.path):
            # Use context manager to insert data
            with database.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (chat_id, access_token) VALUES (?, ?)",
                    ("test_user", "test_token")
                )

            # Verify data was committed
            token_data = database.get_user_token("test_user")
            assert token_data is not None
            assert token_data['access_token'] == "test_token"

    def test_context_manager_rollback_on_error(self):
        """Test that database context manager rolls back on error"""
        with patch('src.db.database.DB_PATH', self.path):
            try:
                with database.get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (chat_id, access_token) VALUES (?, ?)",
                        ("test_user", "test_token")
                    )
                    # Cause an error
                    raise ValueError("Test error")
            except ValueError:
                pass

            # Data should not be committed
            token_data = database.get_user_token("test_user")
            assert token_data is None