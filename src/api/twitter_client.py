import os
import secrets
from xdk import Client
from xdk.oauth2_auth import OAuth2PKCEAuth

class TwitterManager:
    def __init__(self):
        self.client_id = os.getenv("X_CLIENT_ID")
        self.redirect_uri = os.getenv("X_REDIRECT_URI")
        self.scope = "tweet.read users.read offline.access"

    def create_oauth_session(self):
        """Create OAuth2 PKCE session and return auth URL, state, and code_verifier"""
        auth = OAuth2PKCEAuth(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        state = secrets.token_urlsafe(32)
        auth_url = auth.get_authorization_url(state=state)
        return auth_url, state, auth.code_verifier

    def exchange_code_for_token(self, authorization_response, code_verifier):
        """Exchange authorization code for access token"""
        auth = OAuth2PKCEAuth(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        auth.code_verifier = code_verifier
        token = auth.fetch_token(authorization_response=authorization_response)
        return token

    def fetch_home_timeline(self, access_token, max_results=20):
        """Fetch tweets from user's home timeline/feed"""
        client = Client(access_token=access_token)
        tweets = []

        try:
            # Get the authenticated user's ID first
            user_response = client.users.get_me()
            if not user_response.data:
                return tweets

            user_id = user_response.data.get("id")

            # Fetch reverse chronological home timeline
            # Note: XDK's home timeline endpoint
            response = client.users.get_timeline(
                id=user_id,
                max_results=min(max_results, 100)
            )

            if response.data:
                tweets = response.data[:max_results]
        except Exception as e:
            print(f"Error fetching home timeline: {e}")

        return tweets

    def refresh_access_token(self, refresh_token):
        """Refresh the access token using refresh token"""
        auth = OAuth2PKCEAuth(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        try:
            new_token = auth.refresh_token(refresh_token=refresh_token)
            return new_token
        except Exception as e:
            print(f"Error refreshing token: {e}")
            return None
