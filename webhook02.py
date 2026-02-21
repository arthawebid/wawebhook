from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import threading
import requests
import time

app = Flask(__name__)

DATA_DIR = "data"
SESSION_FILE = os.path.join(DATA_DIR, "sessions03.json")
MESSAGE_FILE = os.path.join(DATA_DIR, "messages03.json")

# =========================
# CONFIG N8N
# =========================

N8N_SESSION_WEBHOOK = "https://n8n.app.bkr/webhook-test/session"
N8N_MESSAGE_WEBHOOK = "https://n8n.app.bkr/webhook-test/message"

# Jika sudah install CA ke system → pakai True
#VERIFY_SSL = True
# Jika belum → isi path CA mkcert
VERIFY_SSL = "/home/dev/.local/share/mkcert/rootCA.pem"

REQUEST_TIMEOUT = 10
RETRY_COUNT = 3

lock = threading.Lock()


# =========================
# Utilities
# =========================

def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}")


def ensure_storage():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    for file in [SESSION_FILE, MESSAGE_FILE]:
        if not os.path.exists(file):
            with open(file, "w") as f:
                json.dump([], f)


def safe_read_json(path):
    try:
        with open(path, "r") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except Exception as e:
        log(f"JSON READ ERROR: {e}")
        return []


def safe_write_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"JSON WRITE ERROR: {e}")


def append_json(path, payload):
    with lock:
        ensure_storage()
        data = safe_read_json(path)
        data.append(payload)
        safe_write_json(path, data)


# =========================
# Forward to n8n
# =========================

def forward_to_n8n(url, payload):
    for attempt in range(RETRY_COUNT):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=REQUEST_TIMEOUT,
                verify=VERIFY_SSL
            )

            log(f"Forwarded to n8n → {response.status_code}")
            return response.status_code

        except Exception as e:
            log(f"Forward attempt {attempt+1} failed: {e}")
            time.sleep(2)

    log("All retries failed")
    return None


# =========================
# Routes
# =========================

@app.route("/webhook/session", methods=["POST"])
def webhook_session():
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        log(f"SESSION EVENT: {data}")

        record = {
            "timestamp": datetime.now().isoformat(),
            "session": data.get("session"),
            "status": data.get("status"),
            "raw": data
        }

        append_json(SESSION_FILE, record)

        # Forward ke n8n
        forward_to_n8n(N8N_SESSION_WEBHOOK, record)

        return jsonify({"ok": True})

    except Exception as e:
        log(f"SESSION ERROR: {str(e)}")
        return jsonify({"error": "Server error"}), 500


@app.route("/webhook/message", methods=["POST"])
def webhook_message():
    try:
        data = request.get_json(force=True, silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        log(f"MESSAGE EVENT: {data}")

        record = {
            "timestamp": datetime.now().isoformat(),
            "session": data.get("session"),
            "from": data.get("from"),
            "message": data.get("message"),
            "raw": data
        }

        append_json(MESSAGE_FILE, record)

        # Forward ke n8n
        forward_to_n8n(N8N_MESSAGE_WEBHOOK, record)

        return jsonify({"ok": True})

    except Exception as e:
        log(f"MESSAGE ERROR: {str(e)}")
        return jsonify({"error": "Server error"}), 500


@app.route("/")
def home():
    return "WA Webhook Server Running with n8n Forward"


# =========================
# Start
# =========================

if __name__ == "__main__":
    ensure_storage()
    app.run(host="0.0.0.0", port=3335)