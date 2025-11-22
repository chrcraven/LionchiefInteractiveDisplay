#!/bin/bash
#
# Raspberry Pi Uninstall Script for LionChief Train Queue System
# This script removes all services, files, and configurations
#

set -e  # Exit on error

echo "=========================================="
echo "LionChief Train Queue - Uninstall Script"
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
PROJECT_ROOT="$SCRIPT_DIR"
API_DIR="$PROJECT_ROOT/api"
UI_DIR="$PROJECT_ROOT/ui"

echo "📂 Project Directory: $PROJECT_ROOT"
echo ""

# Confirm uninstall
echo "⚠️  WARNING: This will remove:"
echo "   - LionChief API systemd service"
echo "   - LionChief UI systemd service (if exists)"
echo "   - Python virtual environments"
echo "   - Service configuration files"
echo ""
read -p "Are you sure you want to uninstall? (yes/no): " -r
echo ""
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "❌ Uninstall cancelled"
    exit 0
fi

# Stop and disable API service
echo "🛑 Stopping LionChief API service..."
if systemctl is-active --quiet lionchief-api.service; then
    sudo systemctl stop lionchief-api.service
    echo "   ✓ Service stopped"
else
    echo "   ℹ️  Service not running"
fi

if systemctl is-enabled --quiet lionchief-api.service 2>/dev/null; then
    sudo systemctl disable lionchief-api.service
    echo "   ✓ Service disabled"
fi

# Remove API service file
if [ -f "/etc/systemd/system/lionchief-api.service" ]; then
    echo "🗑️  Removing API service file..."
    sudo rm -f /etc/systemd/system/lionchief-api.service
    echo "   ✓ Removed /etc/systemd/system/lionchief-api.service"
fi

# Stop and disable UI service (if exists)
echo "🛑 Stopping LionChief UI service..."
if systemctl is-active --quiet lionchief-ui.service 2>/dev/null; then
    sudo systemctl stop lionchief-ui.service
    echo "   ✓ Service stopped"
else
    echo "   ℹ️  Service not running or doesn't exist"
fi

if systemctl is-enabled --quiet lionchief-ui.service 2>/dev/null; then
    sudo systemctl disable lionchief-ui.service
    echo "   ✓ Service disabled"
fi

# Remove UI service file
if [ -f "/etc/systemd/system/lionchief-ui.service" ]; then
    echo "🗑️  Removing UI service file..."
    sudo rm -f /etc/systemd/system/lionchief-ui.service
    echo "   ✓ Removed /etc/systemd/system/lionchief-ui.service"
fi

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload
sudo systemctl reset-failed

# Remove virtual environments
echo "🗑️  Removing Python virtual environments..."
if [ -d "$API_DIR/venv" ]; then
    rm -rf "$API_DIR/venv"
    echo "   ✓ Removed API virtual environment"
fi

if [ -d "$UI_DIR/venv" ]; then
    rm -rf "$UI_DIR/venv"
    echo "   ✓ Removed UI virtual environment"
fi

# Remove Python cache files
echo "🗑️  Removing Python cache files..."
find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -type f -name "*.pyc" -delete 2>/dev/null || true
echo "   ✓ Cleaned up cache files"

# Remove data files
echo "🗑️  Removing data files..."
if [ -f "$API_DIR/analytics.json" ]; then
    rm -f "$API_DIR/analytics.json"
    echo "   ✓ Removed analytics.json"
fi

if [ -f "$API_DIR/scheduled_jobs.json" ]; then
    rm -f "$API_DIR/scheduled_jobs.json"
    echo "   ✓ Removed scheduled_jobs.json"
fi

if [ -f "$API_DIR/profanity_custom.json" ]; then
    rm -f "$API_DIR/profanity_custom.json"
    echo "   ✓ Removed profanity_custom.json"
fi

# Ask about .env file
echo ""
read -p "Do you want to remove the .env configuration file? (yes/no): " -r
echo ""
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    if [ -f "$PROJECT_ROOT/.env" ]; then
        rm -f "$PROJECT_ROOT/.env"
        echo "   ✓ Removed .env file"
    fi
else
    echo "   ℹ️  Keeping .env file for future use"
fi

# Remove user from bluetooth group
echo ""
read -p "Do you want to remove user from bluetooth group? (yes/no): " -r
echo ""
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    sudo gpasswd -d $USER bluetooth 2>/dev/null || true
    echo "   ✓ Removed from bluetooth group"
    echo "   ⚠️  Log out and back in for group change to take effect"
else
    echo "   ℹ️  User remains in bluetooth group"
fi

echo ""
echo "=========================================="
echo "✅ Uninstall Complete!"
echo "=========================================="
echo ""
echo "The following have been removed:"
echo "  ✓ LionChief API systemd service"
echo "  ✓ LionChief UI systemd service (if existed)"
echo "  ✓ Python virtual environments"
echo "  ✓ Python cache files"
echo "  ✓ Data files (analytics, jobs, profanity)"
echo ""
echo "📂 The project directory remains at:"
echo "   $PROJECT_ROOT"
echo ""
echo "To completely remove the project:"
echo "   cd .."
echo "   rm -rf LionchiefInteractiveDisplay"
echo ""
