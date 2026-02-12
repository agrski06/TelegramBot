import pytest
from unittest.mock import MagicMock, patch, call
import tempfile
import os


class TestBotLogic:
    """Test Telegram bot command handlers"""

    @pytest.fixture(autouse=True)
    def setup_temp_db(self):
        """Setup temporary database for each test"""
        self.fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(self.fd)

        with patch('src.db.database.DB_PATH', self.path):
            from src.db import database
            database.init_db()
            yield

        # Cleanup
        try:
            os.unlink(self.path)
        except:
            pass

    @pytest.fixture
    def mock_message(self):
        """Create mock Telegram message"""
        message = MagicMock()
        message.chat.id = 123456
        return message

    @pytest.fixture
    def mock_bot(self):
        """Create mock bot"""
        return MagicMock()

    @patch('src.bot.handlers.bot')
    def test_start_command(self, mock_bot, mock_message):
        """Test /start command"""
        from src.bot.handlers import start_command

        start_command(mock_message)

        # Verify welcome message was sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert call_args[0][0] == "123456"  # chat_id
        assert "Welcome to DoomStopper" in call_args[0][1]
        assert "/login" in call_args[0][1]
        assert "/feed" in call_args[0][1]

    @patch('src.bot.handlers.bot')
    def test_help_command(self, mock_bot, mock_message):
        """Test /help command"""
        from src.bot.handlers import help_command

        help_command(mock_message)

        # Should call start_command logic
        mock_bot.send_message.assert_called_once()

    @patch('src.db.database.DB_PATH', '/tmp/test.db')
    @patch('src.bot.handlers.user_exists')
    @patch('src.bot.handlers.bot')
    def test_login_command_already_logged_in(self, mock_bot, mock_user_exists, mock_message):
        """Test /login command when user is already logged in"""
        mock_user_exists.return_value = True

        from src.bot.handlers import login_command

        login_command(mock_message)

        # Verify message about already being logged in
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert "already logged in" in call_args[0][1]

    @patch('src.db.database.DB_PATH', '/tmp/test.db')
    @patch('src.bot.handlers.user_exists')
    @patch('src.bot.handlers.bot')
    def test_login_command_not_logged_in(self, mock_bot, mock_user_exists, mock_message):
        """Test /login command for new user"""
        mock_user_exists.return_value = False

        from src.bot.handlers import login_command

        login_command(mock_message)

        # Verify login instructions were sent
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert "login link" in call_args[0][1].lower()

    @patch('src.db.database.DB_PATH', '/tmp/test.db')
    @patch('src.bot.handlers.user_exists')
    @patch('src.bot.handlers.bot')
    def test_feed_command_not_logged_in(self, mock_bot, mock_user_exists, mock_message):
        """Test /feed command when user is not logged in"""
        mock_user_exists.return_value = False

        from src.bot.handlers import feed_command

        feed_command(mock_message)

        # Verify error message
        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        assert "need to connect" in call_args[0][1].lower()

    @patch('src.db.database.DB_PATH', '/tmp/test.db')
    @patch('src.bot.handlers.tw_manager')
    @patch('src.bot.handlers.get_user_token')
    @patch('src.bot.handlers.user_exists')
    @patch('src.bot.handlers.bot')
    def test_feed_command_success(
        self, mock_bot, mock_user_exists, mock_get_token, mock_tw_manager, mock_message, sample_tweets
    ):
        """Test /feed command successfully fetching tweets"""
        mock_user_exists.return_value = True
        mock_get_token.return_value = {
            'access_token': 'test_token',
            'refresh_token': 'refresh_token',
            'expires_at': 9999999999
        }
        mock_tw_manager.fetch_home_timeline.return_value = sample_tweets[:5]

        from src.bot.handlers import feed_command

        feed_command(mock_message)

        # Verify messages were sent
        assert mock_bot.send_message.call_count >= 2  # At least status + digest header
        mock_tw_manager.fetch_home_timeline.assert_called_once_with('test_token', max_results=20)

    @patch('src.db.database.DB_PATH', '/tmp/test.db')
    @patch('src.bot.handlers.bot')
    @patch('src.bot.handlers.get_user_token')
    @patch('src.bot.handlers.user_exists')
    def test_feed_command_no_token(self, mock_user_exists, mock_get_token, mock_bot, mock_message):
        """Test /feed command when token is missing"""
        mock_user_exists.return_value = True
        mock_get_token.return_value = None

        from src.bot.handlers import feed_command

        feed_command(mock_message)

        # Verify error message
        calls = [call[0][1] for call in mock_bot.send_message.call_args_list]
        assert any("Authentication error" in msg for msg in calls)

    @patch('src.bot.handlers.bot')
    def test_send_digest_no_tweets(self, mock_bot):
        """Test sending digest with no tweets"""
        from src.bot.handlers import send_digest

        send_digest("123456", [])

        # Verify no tweets message
        mock_bot.send_message.assert_called_once()
        assert "No new tweets" in mock_bot.send_message.call_args[0][1]

    @patch('src.bot.handlers.bot')
    def test_send_digest_with_tweets(self, mock_bot, sample_tweets):
        """Test sending digest with tweets"""
        from src.bot.handlers import send_digest

        send_digest("123456", sample_tweets[:5])

        # Verify messages were sent (header + 5 tweets + footer)
        assert mock_bot.send_message.call_count == 7
        calls = [call[0][1] for call in mock_bot.send_message.call_args_list]

        # Check header
        assert "Coffee Break Digest" in calls[0]

        # Check tweets
        for i in range(1, 6):
            assert f"Tweet {i}" in calls[i]

        # Check footer
        assert "That's your digest" in calls[6]

    @patch('src.bot.handlers.bot')
    def test_send_digest_long_tweet_truncation(self, mock_bot):
        """Test that long tweets are truncated"""
        from src.bot.handlers import send_digest

        # Create a very long tweet
        class LongTweet:
            def __init__(self):
                self.text = "x" * 1500  # Longer than 1000 character limit

        send_digest("123456", [LongTweet()])

        # Verify tweet was truncated
        calls = [call[0][1] for call in mock_bot.send_message.call_args_list]
        tweet_message = calls[1]  # Second message is the tweet
        assert len(tweet_message) < 1500
        assert "..." in tweet_message

    @patch('src.bot.handlers.bot')
    def test_send_digest_markdown_parse_error(self, mock_bot):
        """Test handling of markdown parsing errors"""
        from src.bot.handlers import send_digest

        # Make markdown parsing fail, fallback to plain text
        mock_bot.send_message.side_effect = [
            None,  # Header succeeds
            Exception("Markdown error"),  # First tweet fails with markdown
            None,  # First tweet succeeds with plain text
            None,  # Footer
        ]

        class SimpleTweet:
            def __init__(self, text):
                self.text = text

        send_digest("123456", [SimpleTweet("Test tweet")])

        # Should attempt to send, fail, then retry
        assert mock_bot.send_message.call_count >= 2

    @patch('src.bot.handlers.bot')
    def test_send_digest_max_tweets(self, mock_bot, sample_tweets):
        """Test sending digest with maximum tweets (20)"""
        from src.bot.handlers import send_digest

        send_digest("123456", sample_tweets)

        # Verify correct number of messages (header + 20 tweets + footer)
        assert mock_bot.send_message.call_count == 22

    @patch('src.bot.handlers.bot')
    def test_send_digest_tweet_without_text_attribute(self, mock_bot):
        """Test handling tweets without text attribute"""
        from src.bot.handlers import send_digest

        # Create tweet-like object without text attribute
        class WeirdTweet:
            def __str__(self):
                return "String representation"

        send_digest("123456", [WeirdTweet()])

        # Should handle it gracefully
        assert mock_bot.send_message.call_count >= 2

    @patch('src.bot.handlers.bot')
    def test_send_digest_complete_failure(self, mock_bot):
        """Test when sending a tweet completely fails"""
        from src.bot.handlers import send_digest

        # Make all tweet sends fail
        def side_effect(*args, **kwargs):
            if "Tweet" in args[1]:
                raise Exception("Send failed")
            return None

        mock_bot.send_message.side_effect = side_effect

        class SimpleTweet:
            def __init__(self, text):
                self.text = text

        # Should not crash
        send_digest("123456", [SimpleTweet("Test")])

        # Header and footer should still be sent
        assert mock_bot.send_message.call_count >= 2