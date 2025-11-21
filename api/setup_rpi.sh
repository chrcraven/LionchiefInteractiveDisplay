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

# Find compatible Python version automatically
echo "🔍 Finding compatible Python version..."

# Function to check if a Python version is compatible
check_python_compatible() {
    local py_cmd=$1
    if ! command -v $py_cmd &> /dev/null; then
        return 1
    fi

    local version=$($py_cmd --version 2>&1 | awk '{print $2}')
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)

    # Compatible if Python 3.7 through 3.12
    if [ "$major" -eq 3 ] && [ "$minor" -ge 7 ] && [ "$minor" -le 12 ]; then
        return 0
    fi
    return 1
}

# Use PYTHON_CMD if specified by user
if [ -n "$PYTHON_CMD" ]; then
    if check_python_compatible "$PYTHON_CMD"; then
        echo "✓ Using user-specified Python: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1 | awk '{print $2}'))"
    else
        echo "❌ ERROR: Specified Python '$PYTHON_CMD' is not compatible"
        exit 1
    fi
else
    # Try to find compatible Python automatically
    PYTHON_CMD=""

    # Try python3.11 and python3.12 first (most likely to be compatible)
    for py_version in python3.11 python3.12 python3.10 python3.9 python3.8 python3; do
        if check_python_compatible "$py_version"; then
            PYTHON_CMD=$py_version
            echo "✓ Found compatible Python: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1 | awk '{print $2}'))"
            break
        fi
    done

    # If no compatible Python found, try to install Python 3.11
    if [ -z "$PYTHON_CMD" ]; then
        echo ""
        echo "⚠️  No compatible Python version found (need Python 3.7-3.12)"
        echo "📦 Attempting to install Python 3.11..."
        echo ""

        sudo apt-get update
        if sudo apt-get install -y python3.11 python3.11-venv python3.11-dev; then
            PYTHON_CMD=python3.11
            echo "✓ Successfully installed Python 3.11"
        else
            echo ""
            echo "❌ ERROR: Could not install Python 3.11 automatically"
            echo ""
            echo "Your system has Python 3.13+ which is incompatible with this application."
            echo "Pydantic v1 (required to avoid Rust compilation) only supports Python 3.7-3.12"
            echo ""
            echo "Please manually install a compatible Python version:"
            echo "  sudo apt-get install python3.11 python3.11-venv python3.11-dev"
            echo ""
            echo "Then run this script again."
            exit 1
        fi
    fi
fi

echo ""

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
WorkingDirectory=$PROJECT_ROOT
Environment="PATH=$API_DIR/venv/bin"
Environment="PYTHONPATH=$PROJECT_ROOT"
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
