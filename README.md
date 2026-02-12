# DoomStopper

A Telegram bot that helps you avoid endless Twitter/X scrolling by sending you a curated digest of 20 tweets from your feed.

## Features

- Get 20 tweets from your Twitter feed on command
- Automatic daily digest at 10:30 AM
- Secure OAuth 2.0 authentication with Twitter
- SQLite database for user management
- Ready for Railway deployment

## Setup

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Twitter/X API credentials (Client ID from [Twitter Developer Portal](https://developer.twitter.com/))

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd DoomStopper
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

5. Configure your `.env` file:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
X_CLIENT_ID=your_x_client_id
X_REDIRECT_URI=http://localhost:5000/callback
BASE_URL=http://localhost:5000
PORT=5000
```

6. Run the application:
```bash
python app.py
```

### Railway Deployment

1. Push your code to GitHub

2. Create a new project on [Railway](https://railway.app)

3. Connect your GitHub repository

4. Add environment variables in Railway:
   - `TELEGRAM_BOT_TOKEN`
   - `X_CLIENT_ID`
   - `X_REDIRECT_URI` (e.g., `https://your-app.up.railway.app/callback`)
   - `BASE_URL` (e.g., `https://your-app.up.railway.app`)

5. Railway will automatically deploy using the Procfile

6. Update your Twitter app settings with the Railway callback URL


## Usage

### Bot Commands

- /start - Welcome message and instructions
- /help - Show help message
- /login - Connect your Twitter account
- /feed - Get your latest 20 tweets immediately

### Authentication Flow

1. Start the bot: `/start`
2. Login: `/login`
3. Click the authentication link
4. Authorize the app on Twitter
5. You'll be redirected back and receive a confirmation message
6. Use `/feed` to get tweets anytime

### Scheduled Digest

Once authenticated, the bot will automatically send you 20 tweets from your feed every day at 10:30 AM.

## Testing

Running Tests
```bash
pytest
```

---

Made with care to help you avoid doom scrolling
