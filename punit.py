import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

# ------------------- CONFIGURATION -------------------
# Enter your Telegram Bot Token here
BOT_TOKEN = "8766442026:AAErxey1uoQJnki4RosBcNXqciIpOCXQfdY"

# Enter your External API URL here
EXTERNAL_API_URL = "PunitNumberDetail_bot"

# Port for the dummy HTTP server
PORT = 8080
# ------------------------------------------------------


# DUMMY HTTP SERVER
class DummyHTTPHandler(BaseHTTPRequestHandler):
    """Simple HTTP server handler to respond to web health checks."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot HTTP Server is Running")

    def log_message(self, format, *args):
        # Suppress logging to keep console output clean
        pass


def run_dummy_server(port):
    """Starts the background HTTP server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, DummyHTTPHandler)
    httpd.serve_forever()


# TELEGRAM BOT LOGIC
def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    """Sends a message using Telegram's sendMessage endpoint."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}")
        return None


def fetch_external_data(phone_number):
    """Calls the external API and fetches JSON data."""
    if not EXTERNAL_API_URL:
        return {"error": "EXTERNAL_API_URL variable is empty."}

    try:
        params = {"phone": phone_number}
        response = requests.get(EXTERNAL_API_URL, params=params, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": f"API Request Failed: {str(e)}"}


def handle_update(update):
    """Processes incoming Telegram updates."""
    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    # 1. Handle /start Command
    if text == "/start":
        welcome_text = "👋 Welcome to the Bot!\nPlease select an option below:"
        keyboard = {
            "keyboard": [[{"text": "📱 Phone Lookup"}]],
            "resize_keyboard": True
        }
        send_message(chat_id, welcome_text, reply_markup=keyboard)

    # 2. Handle "📱 Phone Lookup" Button
    elif text == "📱 Phone Lookup":
        prompt_text = "📞 Send 10 digit mobile number:"
        send_message(chat_id, prompt_text)

    # 3. Handle 10-Digit Mobile Number
    elif text.isdigit() and len(text) == 10:
        send_message(chat_id, "⏳ Processing request, please wait...")

        api_data = fetch_external_data(text)

        # Convert to formatted JSON
        formatted_json = json.dumps(api_data, indent=2, ensure_ascii=False)

        # Sanitize HTML entity characters inside <pre> tags
        formatted_json = (
            formatted_json.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        response_text = f"<pre>{formatted_json}</pre>"
        send_message(chat_id, response_text, parse_mode="HTML")

    # 4. Handle Invalid Input
    else:
        error_text = "⚠️ Invalid input. Please send a valid 10-digit mobile number or tap '📱 Phone Lookup'."
        send_message(chat_id, error_text)


def main():
    if not BOT_TOKEN:
        print("[CRITICAL] BOT_TOKEN variable is blank. Please specify a valid token.")
        return

    # Start the Dummy HTTP Server in a separate daemon thread
    server_thread = threading.Thread(target=run_dummy_server, args=(PORT,), daemon=True)
    server_thread.start()
    print(f"Dummy HTTP server started on port {PORT}.")

    print("🤖 Bot started successfully. Listening for commands via long polling...")
    offset = None

    # Long polling loop
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            response = requests.get(url, params=params, timeout=35)
            data = response.json()

            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    offset = update["update_id"] + 1
                    handle_update(update)

        except requests.exceptions.RequestException as e:
            print(f"[WARNING] Network issue during polling: {e}. Retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"[ERROR] Unexpected loop error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
