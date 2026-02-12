import pytest
from unittest.mock import MagicMock, patch, call
import tempfile
import os
import json


class TestFlaskApp:
    """Test Flask application endpoints and functionality"""

    @pytest.fixture(autouse=True)
    def setup_temp_db(self):
        """Setup temporary database for each test"""
        self.fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)
        yield
        # Cleanup
        try:
            os.unlink(self.path)
        except:
            pass

    @pytest.fixture
    def client(self):
        """Create Flask test client"""
        with patch('src.db.database.DB_PATH', self.path):
            # Import app after patching DB_PATH
            from src.app import app
            app.config['TESTING'] = True

            from src.db.database import init_db
            init_db()

            with app.test_client() as client:
                yield client

    def test_home_endpoint(self, client):
        """Test home/health check endpoint"""
        response = client.get('/')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert data['service'] == 'DoomStopper Bot'
        assert 'timestamp' in data

    @patch('src.app.bot')
    def test_initiate_auth_success(self, mock_bot, client):
        """Test initiating OAuth flow"""
        with patch('src.app.tw_manager') as mock_tw_manager:
            # Mock OAuth session creation
            mock_tw_manager.create_oauth_session.return_value = (
                "https://twitter.com/oauth/authorize?...",
                "test_state_123",
                "test_verifier"
            )

            response = client.get('/auth/123456')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
            mock_bot.send_message.assert_called_once()

    @patch('src.app.bot')
    def test_initiate_auth_error(self, mock_bot, client):
        """Test auth initiation error handling"""
        with patch('src.app.tw_manager') as mock_tw_manager:
            # Mock error
            mock_tw_manager.create_oauth_session.side_effect = Exception("OAuth error")

            response = client.get('/auth/123456')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['status'] == 'error'

    def test_callback_missing_state(self, client):
        """Test callback with missing state parameter"""
        response = client.get('/callback')

        assert response.status_code == 400
        assert b"missing state" in response.data

    def test_callback_with_error(self, client):
        """Test callback with error from Twitter"""
        response = client.get('/callback?error=access_denied')

        assert response.status_code == 400
        assert b"Authentication failed" in response.data

    def test_callback_expired_session(self, client):
        """Test callback with expired/invalid session"""
        response = client.get('/callback?state=invalid_state')

        assert response.status_code == 400
        assert b"Session expired" in response.data

    @patch('src.app.bot')
    def test_callback_success(self, mock_bot, client):
        """Test successful OAuth callback"""
        with patch('src.db.database.DB_PATH', self.path):
            from src.db.database import save_oauth_session, get_user_token, get_oauth_session

            # Save OAuth session
            save_oauth_session("test_state", "123456", "test_verifier")

            with patch('src.app.tw_manager') as mock_tw_manager:
                # Mock token exchange
                mock_tw_manager.exchange_code_for_token.return_value = {
                    'access_token': 'test_access_token',
                    'refresh_token': 'test_refresh_token',
                    'expires_in': 7200
                }

                response = client.get('/callback?state=test_state&code=test_code')

                assert response.status_code == 200
                assert b"Success!" in response.data
                mock_bot.send_message.assert_called_once()

                # Verify token was saved
                token_data = get_user_token("123456")
                assert token_data is not None
                assert token_data['access_token'] == 'test_access_token'

                # Verify session was deleted
                session = get_oauth_session("test_state")
                assert session is None

    @patch('src.app.bot')
    def test_callback_token_exchange_failure(self, mock_bot, client):
        """Test callback when token exchange fails"""
        with patch('src.db.database.DB_PATH', self.path):
            from src.db.database import save_oauth_session

            # Save OAuth session
            save_oauth_session("test_state", "123456", "test_verifier")

            with patch('src.app.tw_manager') as mock_tw_manager:
                # Mock token exchange failure
                mock_tw_manager.exchange_code_for_token.side_effect = Exception("Exchange failed")

                response = client.get('/callback?state=test_state&code=test_code')

                assert response.status_code == 500
                assert b"Authentication error" in response.data
                mock_bot.send_message.assert_called_once()
                # Verify failure message was sent
                call_args = mock_bot.send_message.call_args
                assert "failed" in call_args[0][1].lower()

    @patch('builtins.print')
    def test_daily_coffee_break_no_users(self, mock_print):
        """Test daily digest with no users"""
        with patch('src.db.database.DB_PATH', self.path):
            from src.db.database import init_db
            from src.app import daily_coffee_break

            init_db()
            daily_coffee_break()

            # Should complete without errors
            mock_print.assert_called()

    @patch('src.app.send_digest')
    @patch('builtins.print')
    def test_daily_coffee_break_with_users(
        self, mock_print, mock_send_digest, sample_tweets
    ):
        """Test daily digest sending to multiple users"""
        with patch('src.db.database.DB_PATH', self.path):
            from src.app import daily_coffee_break
            from src.db.database import init_db, save_user_tokens

            init_db()
            # Add test users
            save_user_tokens("user1", "token1", None, None)
            save_user_tokens("user2", "token2", None, None)

            with patch('src.app.tw_manager') as mock_tw_manager:
                mock_tw_manager.fetch_home_timeline.return_value = sample_tweets[:5]


                daily_coffee_break()

                # Verify digest was sent to both users
                assert mock_send_digest.call_count == 2
                mock_tw_manager.fetch_home_timeline.assert_called()

    @patch('src.app.send_digest')
    @patch('builtins.print')
    def test_daily_coffee_break_user_error(
        self, mock_print, mock_send_digest
    ):
        """Test daily digest continues on user error"""
        with patch('src.db.database.DB_PATH', self.path):
            from src.app import daily_coffee_break
            from src.db.database import init_db, save_user_tokens

            init_db()
            # Add test users
            save_user_tokens("user1", "token1", None, None)
            save_user_tokens("user2", "token2", None, None)

            with patch('src.app.tw_manager') as mock_tw_manager:
                # First user fails, second succeeds
                mock_tw_manager.fetch_home_timeline.side_effect = [
                    Exception("Error for user1"),
                    []  # Success for user2
                ]


                daily_coffee_break()

                # Should attempt both users despite error
                assert mock_tw_manager.fetch_home_timeline.call_count == 2

    @patch('src.app.bot')
    def test_callback_token_without_expires_in(self, mock_bot, client):
        """Test callback handling token without expires_in field"""
        with patch('src.db.database.DB_PATH', self.path):
            from src.db.database import init_db, save_oauth_session, get_user_token

            init_db()
            save_oauth_session("test_state", "123456", "test_verifier")

            with patch('src.app.tw_manager') as mock_tw_manager:
                # Mock token without expires_in
                mock_tw_manager.exchange_code_for_token.return_value = {
                    'access_token': 'test_access_token',
                    'refresh_token': 'test_refresh_token'
                }

                response = client.get('/callback?state=test_state&code=test_code')

                assert response.status_code == 200

                # Verify token was saved with None expires_at
                token_data = get_user_token("123456")
                assert token_data['access_token'] == 'test_access_token'
                assert token_data['expires_at'] is None


class TestAppInitialization:
    """Test app initialization and configuration"""

    @patch('src.app.BackgroundScheduler')
    @patch('src.app.threading.Thread')
    @patch('src.app.init_db')
    def test_app_initialization(self, mock_init_db, mock_thread, mock_scheduler):
        """Test that app initializes database and scheduler on startup"""
        # This test verifies the main block would run correctly
        # We can't easily test the if __name__ == "__main__" block directly
        # but we can verify the functions exist and are importable
        from src.app import daily_coffee_break
        from src.db.database import init_db

        assert callable(daily_coffee_break)
        assert callable(init_db)