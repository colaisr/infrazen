import requests
import websocket
import threading
import json
import time
import os
from dotenv import load_dotenv

load_dotenv('config.dev.env')
FLASK_BASE_URL = "http://127.0.0.1:5001"
AGENT_WS_URL_BASE = "ws://127.0.0.1:8001/v1/chat/rec/"

# Using the correct demo user credentials from the seeding script
DEMO_USER_EMAIL = 'demo@infrazen.com'
DEMO_USER_PASSWORD = 'demo'

RECOMMENDATION_ID_TO_TEST = None # Will be fetched dynamically

def log_step(message):
    print(f"\n{'='*20}\n[STEP] {message}\n{'='*20}")

def log_info(message):
    print(f"[INFO] {message}")

def log_success(message):
    print(f"[SUCCESS] ✅ {message}")

def log_error(message):
    print(f"[ERROR] ❌ {message}")
    
def log_ws(prefix, message):
    print(f"[WS {prefix}] {message}")

class TestWebSocketClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self.thread = None
        self.is_connected = False
        self.received_messages = []

    def on_message(self, ws, message):
        log_ws("RECV", message)
        self.received_messages.append(json.loads(message))

    def on_error(self, ws, error):
        log_ws("ERROR", str(error))
        self.is_connected = False

    def on_close(self, ws, close_status_code, close_msg):
        log_ws("CLOSE", f"Code: {close_status_code}, Msg: {close_msg}")
        self.is_connected = False

    def on_open(self, ws):
        log_ws("OPEN", "Connection opened.")
        self.is_connected = True
        # Don't send a message immediately, just verify the connection stays open

    def connect(self):
        log_info(f"Connecting to WebSocket at: {self.ws_url}")
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()
        # Wait a moment for the connection to establish or fail
        time.sleep(3) 

    def close(self):
        if self.is_connected:
            self.ws.close()
            log_info("WebSocket connection closed.")

if __name__ == "__main__":
    session = requests.Session()
    jwt_token = None

    # Step 1: Login to Flask app to get a session cookie
    try:
        log_step("1. Authenticating with Flask app")
        login_url = f"{FLASK_BASE_URL}/api/auth/login-password"
        login_payload = {
            "username": DEMO_USER_EMAIL,
            "password": DEMO_USER_PASSWORD
        }
        log_info(f"Posting to {login_url} with user {DEMO_USER_EMAIL}")
        response = session.post(login_url, json=login_payload)

        if response.status_code == 200 and response.json().get('success'):
            log_success("Login successful. Session cookie obtained.")
        else:
            log_error(f"Login failed. Status: {response.status_code}, Response: {response.text[:200]}")
            exit(1)
    except requests.exceptions.RequestException as e:
        log_error(f"Failed to connect to Flask app at {FLASK_BASE_URL}. Is it running?")
        log_error(f"Error: {e}")
        exit(1)

    # Step 2: Fetch a valid recommendation ID for the logged-in user
    try:
        log_step("2. Fetching a valid recommendation ID")
        rec_api_url = f"{FLASK_BASE_URL}/api/recommendations"
        log_info(f"Getting recommendations from {rec_api_url}")
        response = session.get(rec_api_url)
        
        if response.status_code == 200:
            recs = response.json().get('recommendations', [])
            if recs:
                RECOMMENDATION_ID_TO_TEST = recs[0].get('id')
                log_success(f"Found a valid recommendation ID to use for the test: {RECOMMENDATION_ID_TO_TEST}")
            else:
                log_error("Could not find any recommendations for the demo user.")
                exit(1)
        else:
            log_error(f"Failed to fetch recommendations. Status: {response.status_code}, Response: {response.text[:200]}")
            exit(1)
    except requests.exceptions.RequestException as e:
        log_error(f"Error fetching recommendations: {e}")
        exit(1)

    # Step 3: Use the session cookie to get a JWT from the API
    if RECOMMENDATION_ID_TO_TEST:
        try:
            log_step(f"3. Requesting JWT for recommendation ID: {RECOMMENDATION_ID_TO_TEST}")
            token_url = f"{FLASK_BASE_URL}/api/chat/token"
            token_payload = {"recommendation_id": RECOMMENDATION_ID_TO_TEST}
            log_info(f"Posting to {token_url}")
            response = session.post(token_url, json=token_payload)

            if response.status_code == 200:
                token_data = response.json()
                jwt_token = token_data.get('token')
                log_success("JWT obtained successfully.")
                log_info(f"Token (first 30 chars): {jwt_token[:30]}...")
            else:
                log_error(f"Failed to get JWT. Status: {response.status_code}, Response: {response.text}")
                exit(1)
        except requests.exceptions.RequestException as e:
            log_error(f"Error requesting JWT: {e}")
            exit(1)

    # Step 4: Connect to the WebSocket using the JWT
    if jwt_token:
        log_step("4. Connecting to Agent WebSocket with JWT")
        ws_url = f"{AGENT_WS_URL_BASE}{RECOMMENDATION_ID_TO_TEST}?token={jwt_token}"
        ws_client = TestWebSocketClient(ws_url)
        ws_client.connect()
        
        if not ws_client.is_connected:
            log_error("WebSocket connection failed to establish or was closed immediately.")
            log_info("Please check the agent.log for errors.")
        else:
            log_success("WebSocket connection is stable.")
            # Verify we received the system message
            if any(msg.get('type') == 'system' for msg in ws_client.received_messages):
                log_success("Received system 'session active' message from agent.")
            else:
                log_error("Did not receive the expected system message from the agent.")

        # Keep the script running for a moment to observe
        time.sleep(2)
        ws_client.close()

    log_step("Test script finished.")
