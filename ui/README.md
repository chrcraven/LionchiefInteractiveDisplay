# LionChief Train Queue UI

Web interface for the LionChief Train Queue system.

## Features

- Interactive train control interface
- Queue status display
- Multiple theme support
- Admin configuration panel
- Responsive design for desktop and mobile

## Raspberry Pi Installation

### Automatic Setup

Run the setup script to automatically install and configure the UI:

```bash
cd ui
./setup_rpi.sh
```

This will:
- Install system dependencies (Python, pip, venv)
- Create a Python virtual environment
- Install Flask and other Python dependencies
- Create a systemd service for auto-start
- Enable and start the UI service

### Manual Installation

If you prefer to install manually:

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp ../.env.example ../.env
   nano ../.env  # Edit API_URL and other settings
   ```

4. **Run the UI:**
   ```bash
   python app.py
   ```

## Configuration

The UI is configured through environment variables in the `.env` file at the project root:

- `API_URL` - URL of the API server (default: `http://localhost:8000`)
- `SECRET_KEY` - Flask secret key for sessions (set in production)

## Accessing the UI

Once running, access the UI at:

- **Main Interface:** http://your-pi-ip:5000
- **Admin Panel:** http://your-pi-ip:5000/secret-admin
- **Theme Selector:** http://your-pi-ip:5000/secret-admin-theme-selector

## Service Management

If installed as a systemd service:

```bash
# View logs
sudo journalctl -u lionchief-ui.service -f

# Restart service
sudo systemctl restart lionchief-ui.service

# Stop service
sudo systemctl stop lionchief-ui.service

# Start service
sudo systemctl start lionchief-ui.service

# Disable auto-start
sudo systemctl disable lionchief-ui.service
```

## Themes

The UI supports multiple visual themes. Access the theme selector at `/secret-admin-theme-selector` to choose your preferred theme.

## Development

For development:

```bash
# Activate virtual environment
source venv/bin/activate

# Run in debug mode
python app.py
```

The UI will be available at http://localhost:5000 with auto-reload enabled.

## Uninstalling

To uninstall the UI service, run the uninstall script from the project root:

```bash
cd ..
./uninstall_rpi.sh
```

This will remove both the API and UI services.
