"""Spotify OAuth helper for obtaining refresh tokens."""

import base64
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

import httpx

# Scopes needed for playlist creation
SCOPES = [
    "playlist-modify-public",
    "playlist-modify-private",
    "user-read-private",
]


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback."""

    auth_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        """Handle the OAuth callback redirect."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self._send_success_response()
        elif "error" in params:
            OAuthCallbackHandler.error = params["error"][0]
            self._send_error_response(params["error"][0])
        else:
            self._send_error_response("No code or error in callback")

    def _send_success_response(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Spotify Auth Success</title></head>
        <body style="font-family: system-ui; padding: 40px; text-align: center;">
            <h1>Authorization successful!</h1>
            <p>You can close this window and return to the terminal.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _send_error_response(self, error: str):
        self.send_response(400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Spotify Auth Error</title></head>
        <body style="font-family: system-ui; padding: 40px; text-align: center;">
            <h1>Authorization failed</h1>
            <p>Error: {error}</p>
            <p>Please close this window and try again.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        pass


def get_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Build the Spotify authorization URL."""
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(params)


def exchange_code_for_tokens(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    """Exchange authorization code for access and refresh tokens."""
    token_url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    response = httpx.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Authorization": f"Basic {auth_header}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def run_oauth_flow(
    client_id: str,
    client_secret: str,
    redirect_uri: str = "http://localhost:8888/callback",
    timeout: int = 120,
) -> dict:
    """
    Run the complete OAuth flow with a local callback server.

    Args:
        client_id: Spotify client ID
        client_secret: Spotify client secret
        redirect_uri: OAuth redirect URI (must match Spotify app settings)
        timeout: How long to wait for user to authorize (seconds)

    Returns:
        Dict with access_token, refresh_token, expires_in, etc.

    Raises:
        TimeoutError: If user doesn't complete auth within timeout
        RuntimeError: If auth fails for any reason
    """
    # Parse redirect URI to get host and port
    parsed = urllib.parse.urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8888

    # Reset handler state
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.error = None

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(16)

    # Start local server
    server = HTTPServer((host, port), OAuthCallbackHandler)
    server.timeout = timeout

    # Open browser
    auth_url = get_auth_url(client_id, redirect_uri, state)
    webbrowser.open(auth_url)

    # Wait for callback (with timeout)
    def handle_request():
        server.handle_request()

    thread = threading.Thread(target=handle_request)
    thread.start()
    thread.join(timeout=timeout)

    server.server_close()

    if OAuthCallbackHandler.error:
        raise RuntimeError(f"Spotify authorization failed: {OAuthCallbackHandler.error}")

    if not OAuthCallbackHandler.auth_code:
        raise TimeoutError("Authorization timed out. Please try again.")

    # Exchange code for tokens
    tokens = exchange_code_for_tokens(
        code=OAuthCallbackHandler.auth_code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    return tokens


def get_user_id(access_token: str) -> str:
    """Fetch the current user's Spotify ID."""
    response = httpx.get(
        "https://api.spotify.com/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["id"]


def run_oauth_flow_headless(
    client_id: str,
    client_secret: str,
    redirect_uri: str = "http://localhost:8888/callback",
) -> dict:
    """
    Run OAuth flow for headless environments (no browser).

    Prints the auth URL for the user to open manually, then prompts for
    the callback URL after authorization.

    Args:
        client_id: Spotify client ID
        client_secret: Spotify client secret
        redirect_uri: OAuth redirect URI (must match Spotify app settings)

    Returns:
        Dict with access_token, refresh_token, expires_in, etc.

    Raises:
        RuntimeError: If auth fails for any reason
    """
    state = secrets.token_urlsafe(16)
    auth_url = get_auth_url(client_id, redirect_uri, state)

    print("\n" + "=" * 60)
    print("Open this URL in a browser to authorize:")
    print("=" * 60)
    print(f"\n{auth_url}\n")
    print("=" * 60)
    print("\nAfter authorizing, you'll be redirected to a URL like:")
    print(f"  {redirect_uri}?code=XXXX&state=YYYY")
    print("\nPaste the FULL callback URL here (it's OK if the page didn't load):")

    callback_url = input("\nCallback URL: ").strip()

    # Parse the callback URL
    parsed = urllib.parse.urlparse(callback_url)
    params = urllib.parse.parse_qs(parsed.query)

    if "error" in params:
        raise RuntimeError(f"Spotify authorization failed: {params['error'][0]}")

    if "code" not in params:
        raise RuntimeError(
            "No authorization code found in URL. Make sure you pasted the complete callback URL."
        )

    code = params["code"][0]

    # Exchange code for tokens
    tokens = exchange_code_for_tokens(
        code=code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    return tokens
