import telebot
import os
import logging
from telebot import types
from src.db.database import user_exists, get_user_token
from src.api.twitter_client import TwitterManager

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
tw_manager = TwitterManager()

logger = logging.getLogger(__name__)

@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    chat_id = str(message.chat.id)

    welcome_text = """
👋 Welcome to DoomStopper!

This bot helps you avoid endless scrolling by sending you a curated digest of 20 tweets from your Twitter feed.

📱 **Commands:**
/login - Connect your Twitter account
/feed - Get your latest 20 tweets now
/help - Show this help message

🕐 **Scheduled Digest:**
Once you connect your account, I'll automatically send you 20 tweets every day at 10:30 AM.

Let's get started! Use /login to connect your Twitter account.
    """
    bot.send_message(chat_id, welcome_text)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle /help command"""
    start_command(message)

@bot.message_handler(commands=['login'])
def login_command(message):
    """Handle /login command"""
    chat_id = str(message.chat.id)
    logger.info(f"Login request received from chat_id: {chat_id}")
    from src.db.database import user_exists

    if user_exists(chat_id):
        logger.info(f"User {chat_id} already logged in")
        bot.send_message(chat_id, "✅ You're already logged in! Use /feed to get your tweets.")
        return

    # Generate auth URL
    base_url = os.getenv("BASE_URL", "http://localhost:5000")
    auth_endpoint = f"{base_url}/auth/{chat_id}"
    logger.info(f"Generated auth endpoint for {chat_id}: {auth_endpoint}")

    bot.send_message(
        chat_id,
        f"🔐 To connect your Twitter account, click here:\n\n{auth_endpoint}"
    )
    logger.info(f"Sent login auth endpoint to {chat_id}")

@bot.message_handler(commands=['feed'])
def feed_command(message):
    """Handle /feed command - fetch and send tweets immediately"""
    chat_id = str(message.chat.id)

    if not user_exists(chat_id):
        bot.send_message(
            chat_id,
            "❌ You need to connect your Twitter account first!\n\n"
            "Use /login to get started."
        )
        return

    bot.send_message(chat_id, "📡 Fetching your feed... This may take a moment.")

    # Get user token
    token_data = get_user_token(chat_id)
    if not token_data or not token_data['access_token']:
        bot.send_message(chat_id, "❌ Authentication error. Please /login again.")
        return

    # Fetch tweets
    tweets = tw_manager.fetch_home_timeline(token_data['access_token'], max_results=20)
    send_digest(chat_id, tweets)

def send_digest(chat_id, tweets):
    """Send tweet digest to user"""
    if not tweets:
        bot.send_message(chat_id, "☕️ No new tweets in your feed right now.")
        return

    bot.send_message(
        chat_id,
        f"☕️ *Your Coffee Break Digest*\n📊 {len(tweets)} tweets from your feed",
        parse_mode="Markdown"
    )

    for i, tweet in enumerate(tweets, 1):
        try:
            # Format tweet text
            text = tweet.text if hasattr(tweet, 'text') else str(tweet)

            # Truncate if too long (Telegram has message length limits)
            if len(text) > 1000:
                text = text[:997] + "..."

            message = f"🐦 *Tweet {i}/{len(tweets)}*\n\n{text}"
            bot.send_message(chat_id, message, parse_mode="Markdown")
        except Exception as e:
            # If markdown fails, send as plain text
            try:
                bot.send_message(chat_id, f"🐦 Tweet {i}: {text}")
            except:
                continue

    bot.send_message(
        chat_id,
        "✅ That's your digest! Use /feed anytime to get fresh tweets."
    )