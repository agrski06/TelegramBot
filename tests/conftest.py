import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch

# Set test environment variables with valid token format
os.environ['TELEGRAM_BOT_TOKEN'] = '123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890'
os.environ['X_CLIENT_ID'] = 'test_x_client_id'
os.environ['X_REDIRECT_URI'] = 'http://localhost:5000/callback'
os.environ['BASE_URL'] = 'http://localhost:5000'

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Patch the DB_PATH in database module
    with patch('src.db.database.DB_PATH', path):
        from src.db.database import init_db
        init_db()
        yield path

    # Cleanup
    try:
        os.unlink(path)
    except:
        pass

@pytest.fixture
def mock_bot():
    """Mock Telegram bot"""
    with patch('src.bot.handlers.bot') as mock:
        mock.send_message = MagicMock()
        yield mock

@pytest.fixture
def mock_twitter_client():
    """Mock Twitter/X client"""
    mock = MagicMock()
    mock.users.me.return_value.data.id = "123456789"
    mock.posts.timeline_reverse_chronological.return_value.data = []
    return mock

@pytest.fixture
def sample_tweets():
    """Sample tweet data for testing"""
    class Tweet:
        def __init__(self, text, tweet_id):
            self.text = text
            self.id = tweet_id

    return [
        Tweet(f"This is test tweet number {i}", str(i))
        for i in range(1, 21)
    ]

@pytest.fixture
def flask_app():
    """Create Flask app for testing"""
    from src.app import app
    app.config['TESTING'] = True
    return app

@pytest.fixture
def flask_client(flask_app):
    """Create Flask test client"""
    return flask_app.test_client()