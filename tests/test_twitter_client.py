import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from src.api.twitter_client import TwitterManager


class TestTwitterManager:
    """Test Twitter client operations"""

    @pytest.fixture
    def twitter_manager(self):
        """Create TwitterManager instance"""
        with patch.dict('os.environ', {
            'X_CLIENT_ID': 'test_client_id',
            'X_REDIRECT_URI': 'http://localhost:5000/callback'
        }):
            return TwitterManager()

    def test_init(self, twitter_manager):
        """Test TwitterManager initialization"""
        assert twitter_manager.client_id == 'test_client_id'
        assert twitter_manager.redirect_uri == 'http://localhost:5000/callback'
        assert 'tweet.read' in twitter_manager.scope
        assert 'users.read' in twitter_manager.scope
        assert 'offline.access' in twitter_manager.scope

    @patch('src.api.twitter_client.OAuth2PKCEAuth')
    @patch('src.api.twitter_client.secrets.token_urlsafe')
    def test_create_oauth_session(self, mock_token, mock_oauth, twitter_manager):
        """Test creating OAuth session"""
        # Mock state generation
        mock_token.return_value = "test_state_123"

        # Mock OAuth2PKCEAuth
        mock_auth = MagicMock()
        mock_auth.get_authorization_url.return_value = "https://twitter.com/oauth/authorize?..."
        mock_auth.code_verifier = "test_code_verifier"
        mock_oauth.return_value = mock_auth

        # Create session
        auth_url, state, code_verifier = twitter_manager.create_oauth_session()

        # Verify
        assert auth_url == "https://twitter.com/oauth/authorize?..."
        assert state == "test_state_123"
        assert code_verifier == "test_code_verifier"
        mock_oauth.assert_called_once()

    @patch('src.api.twitter_client.OAuth2PKCEAuth')
    def test_exchange_code_for_token(self, mock_oauth, twitter_manager):
        """Test exchanging authorization code for token"""
        # Mock OAuth2PKCEAuth
        mock_auth = MagicMock()
        mock_auth.fetch_token.return_value = {
            'access_token': 'test_access_token',
            'refresh_token': 'test_refresh_token',
            'expires_in': 7200
        }
        mock_oauth.return_value = mock_auth

        # Exchange code
        token = twitter_manager.exchange_code_for_token(
            authorization_response="http://localhost:5000/callback?code=test_code",
            code_verifier="test_verifier"
        )

        # Verify
        assert token['access_token'] == 'test_access_token'
        assert token['refresh_token'] == 'test_refresh_token'
        assert mock_auth.fetch_token.called

    @patch('src.api.twitter_client.Client')
    def test_fetch_home_timeline_success(self, mock_client_class, twitter_manager, sample_tweets):
        """Test successfully fetching home timeline"""
        # Mock Client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock user response
        mock_user_response = MagicMock()
        mock_user_response.data.id = "123456789"
        mock_client.users.me.return_value = mock_user_response

        # Mock timeline response
        mock_timeline_response = MagicMock()
        mock_timeline_response.data = sample_tweets
        mock_client.posts.timeline_reverse_chronological.return_value = mock_timeline_response

        # Fetch timeline
        tweets = twitter_manager.fetch_home_timeline("test_token", max_results=20)

        # Verify
        assert len(tweets) == 20
        assert tweets[0].text == "This is test tweet number 1"
        mock_client_class.assert_called_once_with(access_token="test_token")
        mock_client.users.me.assert_called_once()
        mock_client.posts.timeline_reverse_chronological.assert_called_once()

    @patch('src.api.twitter_client.Client')
    def test_fetch_home_timeline_no_user_data(self, mock_client_class, twitter_manager):
        """Test fetching timeline when user data is not available"""
        # Mock Client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock user response with no data
        mock_user_response = MagicMock()
        mock_user_response.data = None
        mock_client.users.me.return_value = mock_user_response

        # Fetch timeline
        tweets = twitter_manager.fetch_home_timeline("test_token")

        # Verify
        assert tweets == []
        mock_client.users.me.assert_called_once()

    @patch('src.api.twitter_client.Client')
    def test_fetch_home_timeline_no_tweets(self, mock_client_class, twitter_manager):
        """Test fetching timeline when no tweets are available"""
        # Mock Client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock user response
        mock_user_response = MagicMock()
        mock_user_response.data.id = "123456789"
        mock_client.users.me.return_value = mock_user_response

        # Mock timeline response with no data
        mock_timeline_response = MagicMock()
        mock_timeline_response.data = None
        mock_client.posts.timeline_reverse_chronological.return_value = mock_timeline_response

        # Fetch timeline
        tweets = twitter_manager.fetch_home_timeline("test_token")

        # Verify
        assert tweets == []

    @patch('src.api.twitter_client.Client')
    def test_fetch_home_timeline_with_limit(self, mock_client_class, twitter_manager, sample_tweets):
        """Test fetching timeline with custom max_results"""
        # Create 100 sample tweets
        many_tweets = [MagicMock(text=f"Tweet {i}", id=str(i)) for i in range(100)]

        # Mock Client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock user response
        mock_user_response = MagicMock()
        mock_user_response.data.id = "123456789"
        mock_client.users.me.return_value = mock_user_response

        # Mock timeline response
        mock_timeline_response = MagicMock()
        mock_timeline_response.data = many_tweets
        mock_client.posts.timeline_reverse_chronological.return_value = mock_timeline_response

        # Fetch timeline with limit of 10
        tweets = twitter_manager.fetch_home_timeline("test_token", max_results=10)

        # Verify only 10 tweets returned
        assert len(tweets) == 10

    @patch('src.api.twitter_client.Client')
    @patch('builtins.print')
    def test_fetch_home_timeline_error_with_fallback(
        self, mock_print, mock_client_class, twitter_manager, sample_tweets
    ):
        """Test fallback to user tweets when timeline fails"""
        # Mock Client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock user response
        mock_user_response = MagicMock()
        mock_user_response.data.id = "123456789"
        mock_client.users.me.return_value = mock_user_response

        # Mock timeline to raise exception
        mock_client.posts.timeline_reverse_chronological.side_effect = Exception("Timeline error")

        # Mock fallback user posts
        mock_user_posts = MagicMock()
        mock_user_posts.data = sample_tweets[:5]
        mock_client.posts.get_user_posts.return_value = mock_user_posts

        # Fetch timeline
        tweets = twitter_manager.fetch_home_timeline("test_token", max_results=20)

        # Verify fallback was used
        assert len(tweets) == 5
        mock_client.posts.get_user_posts.assert_called_once()
        mock_print.assert_called()

    @patch('src.api.twitter_client.Client')
    @patch('builtins.print')
    def test_fetch_home_timeline_both_fail(self, mock_print, mock_client_class, twitter_manager):
        """Test when both timeline and fallback fail"""
        # Mock Client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock user response
        mock_user_response = MagicMock()
        mock_user_response.data.id = "123456789"
        mock_client.users.me.return_value = mock_user_response

        # Mock both to raise exceptions
        mock_client.posts.timeline_reverse_chronological.side_effect = Exception("Timeline error")
        mock_client.posts.get_user_posts.side_effect = Exception("Fallback error")

        # Fetch timeline
        tweets = twitter_manager.fetch_home_timeline("test_token")

        # Verify empty list returned
        assert tweets == []
        assert mock_print.call_count == 2  # Both errors printed

    @patch('src.api.twitter_client.OAuth2PKCEAuth')
    def test_refresh_access_token_success(self, mock_oauth, twitter_manager):
        """Test successfully refreshing access token"""
        # Mock OAuth2PKCEAuth
        mock_auth = MagicMock()
        mock_auth.refresh_token.return_value = {
            'access_token': 'new_access_token',
            'refresh_token': 'new_refresh_token',
            'expires_in': 7200
        }
        mock_oauth.return_value = mock_auth

        # Refresh token
        new_token = twitter_manager.refresh_access_token("old_refresh_token")

        # Verify
        assert new_token['access_token'] == 'new_access_token'
        mock_auth.refresh_token.assert_called_once_with(refresh_token="old_refresh_token")

    @patch('src.api.twitter_client.OAuth2PKCEAuth')
    @patch('builtins.print')
    def test_refresh_access_token_failure(self, mock_print, mock_oauth, twitter_manager):
        """Test handling refresh token failure"""
        # Mock OAuth2PKCEAuth
        mock_auth = MagicMock()
        mock_auth.refresh_token.side_effect = Exception("Refresh failed")
        mock_oauth.return_value = mock_auth

        # Refresh token
        new_token = twitter_manager.refresh_access_token("old_refresh_token")

        # Verify
        assert new_token is None
        mock_print.assert_called_once()