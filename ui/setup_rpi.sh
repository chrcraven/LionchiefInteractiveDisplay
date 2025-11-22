#!/bin/bash
#
# Raspberry Pi Setup Script for LionChief Train Queue UI
# This script installs all dependencies and sets up the UI as a systemd service
#

set -e  # Exit on error

echo "=========================================="
echo "LionChief Train Queue UI - Raspberry Pi Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Please do not run this script as root"
    echo "   Run as a regular user with sudo privileges"
    exit 1
fi

# Detect Python version
PYTHON_CMD=${PYTHON_CMD:-python3}
PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "📍 Using Python: $PYTHON_CMD (version $PYTHON_VERSION)"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
UI_DIR="$SCRIPT_DIR"

echo "📂 Project Directory: $PROJECT_ROOT"
echo "📂 UI Directory: $UI_DIR"
echo ""

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
cd "$UI_DIR"
if [ -d "venv" ]; then
    echo "   Virtual environment already exists, removing..."
    rm -rf venv
fi
$PYTHON_CMD -m venv venv

# Activate virtual environment
echo "   Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
echo "⚙️  Configuring environment..."
cd "$PROJECT_ROOT"
if [ ! -f ".env" ]; then
    echo "   Creating .env file from template..."
    cp .env.example .env
    echo "   ⚠️  Please edit .env to configure API_URL and other settings"
else
    echo "   .env file already exists"
fi

# Get API URL from .env or use default
API_URL="http://localhost:8000"
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
fi

# Create systemd service file
echo "🔧 Creating systemd service..."
SERVICE_FILE="/tmp/lionchief-ui.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=LionChief Train Queue UI
After=network.target lionchief-api.service
Wants=lionchief-api.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$UI_DIR
Environment="PATH=$UI_DIR/venv/bin"
Environment="PYTHONPATH=$PROJECT_ROOT"
EnvironmentFile=$PROJECT_ROOT/.env
ExecStart=$UI_DIR/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Install service file
sudo mv "$SERVICE_FILE" /etc/systemd/system/lionchief-ui.service
sudo chmod 644 /etc/systemd/system/lionchief-ui.service

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start service
echo "🚀 Enabling and starting service..."
sudo systemctl enable lionchief-ui.service
sudo systemctl start lionchief-ui.service

# Wait a moment for service to start
sleep 3

# Check service status
echo ""
echo "✅ Setup complete!"
echo ""
echo "=========================================="
echo "Service Status:"
echo "=========================================="
sudo systemctl status lionchief-ui.service --no-pager
echo ""
echo "=========================================="
echo "Useful Commands:"
echo "=========================================="
echo "  View logs:        sudo journalctl -u lionchief-ui.service -f"
echo "  Stop service:     sudo systemctl stop lionchief-ui.service"
echo "  Start service:    sudo systemctl start lionchief-ui.service"
echo "  Restart service:  sudo systemctl restart lionchief-ui.service"
echo "  Disable service:  sudo systemctl disable lionchief-ui.service"
echo ""
echo "📝 Configuration:"
echo "  Edit .env file:   nano $PROJECT_ROOT/.env"
echo "  After editing:    sudo systemctl restart lionchief-ui.service"
echo ""
echo "🌐 UI Access:"
echo "  Main Interface:   http://$(hostname -I | awk '{print $1}'):5000"
echo "  Admin Panel:      http://$(hostname -I | awk '{print $1}'):5000/secret-admin"
echo "  Theme Selector:   http://$(hostname -I | awk '{print $1}'):5000/secret-admin-theme-selector"
echo ""
echo "📡 API Configuration:"
echo "  Current API_URL:  $API_URL"
echo "  (Configure in .env file)"
echo ""
echo "💡 Tip: Run both setup scripts to install the complete system:"
echo "   cd $PROJECT_ROOT/api && ./setup_rpi.sh"
echo "   cd $PROJECT_ROOT/ui && ./setup_rpi.sh"
echo ""
