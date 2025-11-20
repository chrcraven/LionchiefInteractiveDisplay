"""Simple Flask app to serve the UI."""
from flask import Flask, render_template, send_from_directory, request, jsonify, session
import os
import json

from themes import get_theme, get_all_themes, DEFAULT_THEME

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "lionchief-train-secret-key-change-in-production")

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
THEME_FILE = "current_theme.json"


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
