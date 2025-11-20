"""Simple Flask app to serve the UI."""
from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


@app.route("/")
def index():
    """Serve the main UI."""
    return render_template("index.html", api_url=API_URL)


@app.route("/static/<path:path>")
def serve_static(path):
    """Serve static files."""
    return send_from_directory("static", path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
