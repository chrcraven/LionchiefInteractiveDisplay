"""Simple Flask app to serve the UI."""
from flask import Flask, render_template, send_from_directory, request, jsonify, session, Response, stream_with_context
import os
import json
import requests
import threading
import time
import queue
import websocket

from themes import get_theme, get_all_themes, DEFAULT_THEME

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "lionchief-train-secret-key-change-in-production")

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
BASE_PATH = os.getenv("BASE_PATH", "").rstrip('/')  # e.g., "/lionchief" or ""
THEME_FILE = "current_theme.json"

# Configure Flask application root for subdirectory hosting
if BASE_PATH:
    app.config['APPLICATION_ROOT'] = BASE_PATH

# WebSocket to SSE bridge
sse_clients = []
ws_thread = None
ws_connected = False


@app.context_processor
def inject_base_path():
    """Make base_path available to all templates."""
    return {'base_path': BASE_PATH}


def load_current_theme():
    """Load the current theme from file."""
    try:
        if os.path.exists(THEME_FILE):
            with open(THEME_FILE, 'r') as f:
                data = json.load(f)
                return data.get("theme", DEFAULT_THEME)
    except Exception as e:
        print(f"Error loading theme: {e}")
    return DEFAULT_THEME


def save_current_theme(theme_id):
    """Save the current theme to file."""
    try:
        with open(THEME_FILE, 'w') as f:
            json.dump({"theme": theme_id}, f)
        return True
    except Exception as e:
        print(f"Error saving theme: {e}")
        return False


@app.route("/")
def index():
    """Serve the main UI."""
    current_theme_id = load_current_theme()
    theme_data = get_theme(current_theme_id)
    return render_template("index.html", api_url=API_URL, theme=theme_data, theme_id=current_theme_id)


@app.route("/static/<path:path>")
def serve_static(path):
    """Serve static files."""
    return send_from_directory("static", path)


@app.route("/secret-admin")
def admin():
    """Hidden admin page for configuration."""
    return render_template("admin.html", api_url=API_URL)


@app.route("/secret-admin-theme-selector")
def admin_theme():
    """Hidden admin page for theme selection."""
    all_themes = get_all_themes()
    current_theme_id = load_current_theme()
    return render_template("admin_theme.html",
                         themes=all_themes,
                         current_theme=current_theme_id,
                         api_url=API_URL)


@app.route("/api/theme", methods=["GET"])
def get_current_theme():
    """Get the current theme."""
    current_theme_id = load_current_theme()
    theme_data = get_theme(current_theme_id)
    return jsonify({
        "theme_id": current_theme_id,
        "theme": theme_data
    })


@app.route("/api/theme", methods=["POST"])
def set_theme():
    """Set the current theme."""
    data = request.json
    theme_id = data.get("theme_id")

    if not theme_id:
        return jsonify({"success": False, "message": "No theme_id provided"}), 400

    # Verify theme exists
    theme_data = get_theme(theme_id)
    if theme_data is None:
        return jsonify({"success": False, "message": "Invalid theme_id"}), 400

    # Save theme
    if save_current_theme(theme_id):
        return jsonify({
            "success": True,
            "theme_id": theme_id,
            "theme": theme_data
        })
    else:
        return jsonify({"success": False, "message": "Failed to save theme"}), 500


# ============================================================================
# API PROXY ENDPOINTS
# ============================================================================

@app.route("/api/queue/join", methods=["POST"])
def proxy_queue_join():
    """Proxy queue join request to API."""
    try:
        response = requests.post(
            f"{API_URL}/queue/join",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/queue/leave", methods=["POST"])
def proxy_queue_leave():
    """Proxy queue leave request to API."""
    try:
        response = requests.post(
            f"{API_URL}/queue/leave",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/queue/status", methods=["GET"])
def proxy_queue_status():
    """Proxy queue status request to API."""
    try:
        response = requests.get(f"{API_URL}/queue/status", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/train/speed", methods=["POST"])
def proxy_train_speed():
    """Proxy train speed request to API."""
    try:
        response = requests.post(
            f"{API_URL}/train/speed",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/train/direction", methods=["POST"])
def proxy_train_direction():
    """Proxy train direction request to API."""
    try:
        response = requests.post(
            f"{API_URL}/train/direction",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/train/horn", methods=["POST"])
def proxy_train_horn():
    """Proxy train horn request to API."""
    try:
        response = requests.post(
            f"{API_URL}/train/horn",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/train/bell", methods=["POST"])
def proxy_train_bell():
    """Proxy train bell request to API."""
    try:
        response = requests.post(
            f"{API_URL}/train/bell",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/train/emergency-stop", methods=["POST"])
def proxy_train_emergency_stop():
    """Proxy train emergency stop request to API."""
    try:
        response = requests.post(
            f"{API_URL}/train/emergency-stop",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/train/status", methods=["GET"])
def proxy_train_status():
    """Proxy train status request to API."""
    try:
        response = requests.get(f"{API_URL}/train/status", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/config", methods=["GET"])
def proxy_config_get():
    """Proxy config get request to API."""
    try:
        response = requests.get(f"{API_URL}/config", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/config", methods=["POST"])
def proxy_config_post():
    """Proxy config update request to API."""
    try:
        response = requests.post(
            f"{API_URL}/config",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# Admin panel proxy endpoints
@app.route("/api/controls", methods=["GET"])
def proxy_controls_get():
    """Proxy controls config get request to API."""
    try:
        response = requests.get(f"{API_URL}/controls", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/controls", methods=["POST"])
def proxy_controls_post():
    """Proxy controls config update request to API."""
    try:
        response = requests.post(
            f"{API_URL}/controls",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/stats", methods=["GET"])
def proxy_analytics_stats():
    """Proxy analytics stats request to API."""
    try:
        response = requests.get(f"{API_URL}/analytics/stats", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/controls", methods=["GET"])
def proxy_analytics_controls():
    """Proxy analytics controls request to API."""
    try:
        response = requests.get(f"{API_URL}/analytics/controls", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/cleanup", methods=["DELETE"])
def proxy_analytics_cleanup():
    """Proxy analytics cleanup request to API."""
    try:
        days = request.args.get('days', 30)
        response = requests.delete(f"{API_URL}/analytics/cleanup?days={days}", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/profanity-filter", methods=["GET"])
def proxy_profanity_filter_get():
    """Proxy profanity filter get request to API."""
    try:
        response = requests.get(f"{API_URL}/profanity-filter", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/profanity-filter/add", methods=["POST"])
def proxy_profanity_filter_add():
    """Proxy profanity filter add request to API."""
    try:
        word = request.args.get('word', '')
        admin_password = request.args.get('admin_password', '')
        response = requests.post(
            f"{API_URL}/profanity-filter/add?word={word}&admin_password={admin_password}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/profanity-filter/remove", methods=["DELETE"])
def proxy_profanity_filter_remove():
    """Proxy profanity filter remove request to API."""
    try:
        word = request.args.get('word', '')
        admin_password = request.args.get('admin_password', '')
        response = requests.delete(
            f"{API_URL}/profanity-filter/remove?word={word}&admin_password={admin_password}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/profanity-filter/reset", methods=["POST"])
def proxy_profanity_filter_reset():
    """Proxy profanity filter reset request to API."""
    try:
        admin_password = request.args.get('admin_password', '')
        response = requests.post(
            f"{API_URL}/profanity-filter/reset?admin_password={admin_password}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/jobs", methods=["GET"])
def proxy_jobs_get():
    """Proxy jobs get request to API."""
    try:
        response = requests.get(f"{API_URL}/jobs", timeout=10)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/jobs", methods=["POST"])
def proxy_jobs_post():
    """Proxy jobs create request to API."""
    try:
        admin_password = request.args.get('admin_password', '')
        response = requests.post(
            f"{API_URL}/jobs?admin_password={admin_password}",
            json=request.json,
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/jobs/<job_id>", methods=["DELETE"])
def proxy_jobs_delete(job_id):
    """Proxy jobs delete request to API."""
    try:
        admin_password = request.args.get('admin_password', '')
        response = requests.delete(
            f"{API_URL}/jobs/{job_id}?admin_password={admin_password}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/jobs/<job_id>/run", methods=["POST"])
def proxy_jobs_run(job_id):
    """Proxy jobs run request to API."""
    try:
        admin_password = request.args.get('admin_password', '')
        response = requests.post(
            f"{API_URL}/jobs/{job_id}/run?admin_password={admin_password}",
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ============================================================================
# SERVER-SENT EVENTS (SSE) FOR REAL-TIME UPDATES
# ============================================================================

def websocket_to_sse_bridge():
    """Background thread that connects to API WebSocket and broadcasts to SSE clients."""
    global ws_connected

    ws_url = API_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'

    while True:
        try:
            print(f"Connecting to WebSocket: {ws_url}")
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=lambda ws, message: broadcast_to_sse_clients(message),
                on_open=lambda ws: on_ws_open(),
                on_close=lambda ws, close_status_code, close_msg: on_ws_close(),
                on_error=lambda ws, error: on_ws_error(error)
            )
            ws.run_forever()
        except Exception as e:
            print(f"WebSocket error: {e}")
            ws_connected = False
            time.sleep(5)  # Wait before reconnecting


def on_ws_open():
    """Called when WebSocket connection opens."""
    global ws_connected
    ws_connected = True
    print("WebSocket connected to API")
    # Send connection status to all SSE clients
    broadcast_to_sse_clients(json.dumps({"type": "connection_status", "connected": True}))


def on_ws_close():
    """Called when WebSocket connection closes."""
    global ws_connected
    ws_connected = False
    print("WebSocket disconnected from API")
    # Send disconnection status to all SSE clients
    broadcast_to_sse_clients(json.dumps({"type": "connection_status", "connected": False}))


def on_ws_error(error):
    """Called when WebSocket encounters an error."""
    print(f"WebSocket error: {error}")


def broadcast_to_sse_clients(message):
    """Broadcast a message to all connected SSE clients."""
    # Store message in queue for each client
    for client_queue in list(sse_clients):
        try:
            client_queue.put(message)
        except:
            # Remove disconnected clients
            if client_queue in sse_clients:
                sse_clients.remove(client_queue)


@app.route("/api/events")
def sse_stream():
    """Server-Sent Events endpoint for real-time updates."""
    def event_stream():
        # Create a queue for this client
        client_queue = queue.Queue()
        sse_clients.append(client_queue)

        try:
            # Send initial connection status
            yield f"data: {json.dumps({'type': 'connection_status', 'connected': ws_connected})}\n\n"

            # Stream events to this client
            while True:
                try:
                    # Wait for message with timeout
                    message = client_queue.get(timeout=30)
                    yield f"data: {message}\n\n"
                except queue.Empty:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
        finally:
            # Remove this client when connection closes
            if client_queue in sse_clients:
                sse_clients.remove(client_queue)

    return Response(
        stream_with_context(event_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


# Start WebSocket bridge thread
def start_websocket_bridge():
    """Start the WebSocket to SSE bridge in a background thread."""
    global ws_thread
    if ws_thread is None or not ws_thread.is_alive():
        ws_thread = threading.Thread(target=websocket_to_sse_bridge, daemon=True)
        ws_thread.start()
        print("WebSocket to SSE bridge started")


if __name__ == "__main__":
    # Start WebSocket bridge before running the app
    start_websocket_bridge()
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
