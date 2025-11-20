#!/bin/bash
#
# Raspberry Pi Setup Script for LionChief Train Queue API
# This script installs all dependencies and sets up the API as a systemd service
#

set -e  # Exit on error

echo "=========================================="
echo "LionChief Train Queue API - Raspberry Pi Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Please do not run this script as root"
    echo "   Run as a regular user with sudo privileges"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
API_DIR="$SCRIPT_DIR"

echo "📂 Project Directory: $PROJECT_ROOT"
echo "📂 API Directory: $API_DIR"
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
    git \
    bluez \
    bluetooth \
    libbluetooth-dev \
    libglib2.0-dev \
    pkg-config \
    libdbus-1-dev

# Add user to bluetooth group
echo "👤 Adding user to bluetooth group..."
sudo usermod -aG bluetooth $USER

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
cd "$API_DIR"
if [ -d "venv" ]; then
    echo "   Virtual environment already exists, removing..."
    rm -rf venv
fi
python3 -m venv venv

# Activate virtual environment
echo "   Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install pyLionChief
echo "📦 Installing pyLionChief..."
if pip install git+https://github.com/chrcraven/pyLionChief.git; then
    echo "✓ pyLionChief installed successfully"
else
    echo "⚠️  Warning: Could not install pyLionChief"
    echo "   The API will run in mock mode"
fi

# Create .env file if it doesn't exist
echo "⚙️  Configuring environment..."
cd "$PROJECT_ROOT"
if [ ! -f ".env" ]; then
    echo "   Creating .env file from template..."
    cp .env.example .env
    echo "   ⚠️  Please edit .env to set your train's Bluetooth address"
else
    echo "   .env file already exists"
fi

# Create systemd service file
echo "🔧 Creating systemd service..."
SERVICE_FILE="/tmp/lionchief-api.service"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=LionChief Train Queue API
After=network.target bluetooth.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$API_DIR
Environment="PATH=$API_DIR/venv/bin"
EnvironmentFile=$PROJECT_ROOT/.env
ExecStart=$API_DIR/venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Install service file
sudo mv "$SERVICE_FILE" /etc/systemd/system/lionchief-api.service
sudo chmod 644 /etc/systemd/system/lionchief-api.service

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start service
echo "🚀 Enabling and starting service..."
sudo systemctl enable lionchief-api.service
sudo systemctl start lionchief-api.service

# Wait a moment for service to start
sleep 3

# Check service status
echo ""
echo "✅ Setup complete!"
echo ""
echo "=========================================="
echo "Service Status:"
echo "=========================================="
sudo systemctl status lionchief-api.service --no-pager
echo ""
echo "=========================================="
echo "Useful Commands:"
echo "=========================================="
echo "  View logs:        sudo journalctl -u lionchief-api.service -f"
echo "  Stop service:     sudo systemctl stop lionchief-api.service"
echo "  Start service:    sudo systemctl start lionchief-api.service"
echo "  Restart service:  sudo systemctl restart lionchief-api.service"
echo "  Disable service:  sudo systemctl disable lionchief-api.service"
echo ""
echo "📝 Configuration:"
echo "  Edit .env file:   nano $PROJECT_ROOT/.env"
echo "  After editing:    sudo systemctl restart lionchief-api.service"
echo ""
echo "🌐 API Access:"
echo "  API Endpoint:     http://$(hostname -I | awk '{print $1}'):8000"
echo "  API Docs:         http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo "⚠️  IMPORTANT: You may need to log out and log back in for"
echo "   bluetooth group membership to take effect."
echo ""
