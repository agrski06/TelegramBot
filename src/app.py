import os
import threading
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from src.api.twitter_client import TwitterManager
from src.bot.handlers import bot, send_digest
from src.db.database import (
    init_db,
    save_oauth_session,
    get_oauth_session,
    delete_oauth_session,
    save_user_tokens,
    get_all_users,
    get_user_token
)
from datetime import datetime, timedelta

app = Flask(__name__)
tw_manager = TwitterManager()

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "DoomStopper Bot",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/auth/<chat_id>')
def initiate_auth(chat_id):
    """Initiate OAuth flow for a user"""
    try:
        auth_url, state, code_verifier = tw_manager.create_oauth_session()

        # Save session to database
        save_oauth_session(state, chat_id, code_verifier)

        # Send auth URL to user
        bot.send_message(
            chat_id,
            f"🔐 *Connect Your Twitter Account*\n\n"
            f"Click the link below to authorize:\n\n"
            f"{auth_url}\n\n"
            f"After authorizing, you'll be redirected back here.",
            parse_mode="Markdown"
        )

        return jsonify({
            "status": "success",
            "message": "Authorization link sent to Telegram"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/callback')
def callback():
    """Handle OAuth callback from Twitter"""
    state = request.args.get('state')
    error = request.args.get('error')

    if error:
        return f"❌ Authentication failed: {error}", 400

    if not state:
        return "❌ Invalid request: missing state parameter", 400

    # Get session from database
    session = get_oauth_session(state)
    if not session:
        return "❌ Session expired or invalid. Please try /login again in Telegram.", 400

    chat_id = session['chat_id']
    code_verifier = session['code_verifier']

    try:
        # Exchange code for token
        tokens = tw_manager.exchange_code_for_token(
            authorization_response=request.url,
            code_verifier=code_verifier
        )

        # Calculate token expiry
        expires_at = None
        if 'expires_in' in tokens:
            expires_at = int((datetime.now() + timedelta(seconds=tokens['expires_in'])).timestamp())

        # Save tokens to database
        save_user_tokens(
            chat_id=chat_id,
            access_token=tokens.get('access_token'),
            refresh_token=tokens.get('refresh_token'),
            expires_at=expires_at
        )

        # Clean up session
        delete_oauth_session(state)

        # Notify user
        bot.send_message(
            chat_id,
            "✅ *Account Successfully Connected!*\n\n"
            "🎉 You're all set! I'll send you 20 tweets from your feed every day at 10:30 AM.\n\n"
            "💡 Use /feed anytime to get your tweets immediately.",
            parse_mode="Markdown"
        )

        return """
        <html>
        <head>
            <title>Success!</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .success { color: #28a745; font-size: 24px; }
            </style>
        </head>
        <body>
            <h1 class="success">✅ Success!</h1>
            <p>Your Twitter account has been connected.</p>
            <p>You can now close this window and return to Telegram.</p>
        </body>
        </html>
        """
    except Exception as e:
        print(f"OAuth callback error: {e}")
        bot.send_message(
            chat_id,
            "❌ Authentication failed. Please try /login again."
        )
        return f"❌ Authentication error: {str(e)}", 500

# Scheduler Task
def daily_coffee_break():
    """Send daily digest to all users"""
    print(f"[{datetime.now()}] Executing scheduled coffee break...")

    users = get_all_users()
    print(f"Found {len(users)} registered users")

    for chat_id in users:
        try:
            token_data = get_user_token(chat_id)
            if not token_data or not token_data['access_token']:
                continue

            # Fetch tweets
            tweets = tw_manager.fetch_home_timeline(
                token_data['access_token'],
                max_results=20
            )

            # Send digest
            send_digest(chat_id, tweets)
            print(f"Sent digest to {chat_id}")

        except Exception as e:
            print(f"Error sending digest to {chat_id}: {e}")
            continue

    print("Daily coffee break completed!")

# Register login handler with bot
@bot.message_handler(commands=['login'])
def handle_login(message):
    """Handle /login command"""
    chat_id = str(message.chat.id)
    from src.db.database import user_exists

    if user_exists(chat_id):
        bot.send_message(chat_id, "✅ You're already logged in! Use /feed to get your tweets.")
        return

    # Generate auth URL
    base_url = os.getenv("BASE_URL", "http://localhost:5000")
    auth_endpoint = f"{base_url}/auth/{chat_id}"

    bot.send_message(
        chat_id,
        f"🔐 To connect your Twitter account, click here:\n\n{auth_endpoint}"
    )

if __name__ == "__main__":
    # Initialize database
    print("Initializing database...")
    init_db()

    # Start Scheduler
    print("Starting scheduler...")
    scheduler = BackgroundScheduler()
    scheduler.add_job(daily_coffee_break, 'cron', hour=10, minute=30)
    scheduler.start()

    # Start Bot Thread
    print("Starting Telegram bot...")
    threading.Thread(target=bot.infinity_polling, daemon=True).start()

    # Start Flask
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Flask server on port {port}...")
    app.run(host='0.0.0.0', port=port)
