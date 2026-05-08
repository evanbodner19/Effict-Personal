"""One-time Gmail OAuth bootstrap.

Run locally:
    py -3.12 backend/scripts/gmail_oauth_bootstrap.py <CLIENT_ID> <CLIENT_SECRET>

It opens Google's consent page in your browser, captures the redirect, exchanges
the auth code for a refresh token, and prints all three values for you to paste
into Render env vars (GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN).

Requires: a Desktop-app OAuth client in Google Cloud Console with the Gmail API
enabled and yourself listed as a test user. Scope: gmail.readonly.
"""
import http.server
import socketserver
import sys
import threading
import urllib.parse
import webbrowser

import httpx


REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


_received_code: dict[str, str] = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        error = params.get("error", [None])[0]
        if error:
            _received_code["error"] = error
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Error: {error}".encode())
            return
        if code:
            _received_code["code"] = code
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h2>Done. You can close this tab.</h2></body></html>"
        )

    def log_message(self, *_args):
        pass


def main():
    if len(sys.argv) != 3:
        print("usage: gmail_oauth_bootstrap.py <CLIENT_ID> <CLIENT_SECRET>")
        sys.exit(1)
    client_id, client_secret = sys.argv[1], sys.argv[2]

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode(
            {
                "client_id": client_id,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": SCOPE,
                "access_type": "offline",
                "prompt": "consent",
            }
        )
    )

    server = socketserver.TCPServer(("localhost", REDIRECT_PORT), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"Opening: {auth_url}")
    webbrowser.open(auth_url)
    print(f"Listening on {REDIRECT_URI} for the redirect...")

    while "code" not in _received_code and "error" not in _received_code:
        pass
    server.shutdown()

    if "error" in _received_code:
        print(f"OAuth error: {_received_code['error']}")
        sys.exit(1)

    code = _received_code["code"]
    print("Exchanging auth code for tokens...")
    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    resp.raise_for_status()
    tokens = resp.json()
    refresh = tokens.get("refresh_token")
    if not refresh:
        print(
            "No refresh_token returned. Revoke prior consent at "
            "https://myaccount.google.com/permissions and rerun."
        )
        print(tokens)
        sys.exit(1)

    print()
    print("=== Add these to Render env vars ===")
    print(f"GMAIL_CLIENT_ID={client_id}")
    print(f"GMAIL_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={refresh}")


if __name__ == "__main__":
    main()
