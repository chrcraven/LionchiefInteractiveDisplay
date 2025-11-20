# LionChief Interactive Display

A queue-based train control system that allows multiple users to share control of a Lionel LionChief train via a web interface. Perfect for public displays, museums, or train shows where you want to let visitors interact with your train layout.

## Features

- **Queue Management**: Fair FIFO queue system with configurable time slots
- **Single User Infinite Mode**: If only one person is in the queue, they can control the train indefinitely
- **Real-time Updates**: WebSocket-based live queue status and control updates
- **Full Train Control**: Speed, direction, horn, and bell controls
- **Emergency Stop**: Anyone in the queue can trigger an emergency stop
- **Raspberry Pi Ready**: Designed to run on Raspberry Pi with Docker
- **Mock Mode**: Test without a physical train using mock mode

## Architecture

The system consists of two services:

1. **API Service** (FastAPI): Handles queue management, train control, and WebSocket connections
2. **UI Service** (Flask): Serves the web interface for users to join the queue and control the train

## Prerequisites

- Docker and Docker Compose
- Raspberry Pi 4 (or compatible device with Bluetooth)
- LionChief train with Bluetooth connectivity
- Python 3.11+ (if running without Docker)
- [pyLionChief](https://github.com/chrcraven/pyLionChief) library

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/chrcraven/LionchiefInteractiveDisplay.git
cd LionchiefInteractiveDisplay
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your train's Bluetooth address
nano .env
```

Set `TRAIN_ADDRESS` to your train's Bluetooth MAC address (e.g., `AA:BB:CC:DD:EE:FF`). Leave empty to run in mock mode.

### 3. Build and Run with Docker

```bash
docker-compose up -d
```

The services will be available at:
- **UI**: http://localhost:5000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 4. Access the Interface

Open your browser and navigate to `http://localhost:5000` (or your Raspberry Pi's IP address).

## Configuration

Edit the `.env` file to customize settings:

```env
# Train Bluetooth address (leave empty for mock mode)
TRAIN_ADDRESS=AA:BB:CC:DD:EE:FF

# Queue timeout in seconds (default: 300 = 5 minutes)
TRAIN_QUEUE_TIMEOUT=300

# Allow infinite control when only one user (default: true)
TRAIN_ALLOW_INFINITE_SINGLE=true

# API URL for UI to connect (update if using different host/port)
API_URL=http://localhost:8000
```

### Finding Your Train's Bluetooth Address

On Raspberry Pi:

```bash
sudo bluetoothctl
scan on
# Look for your LionChief train in the list
# Note the MAC address
```

## Usage

### For Users

1. **Join Queue**: Enter your name and click "Join Queue"
2. **Wait Your Turn**: See your position in the queue
3. **Control Train**: When it's your turn, use the controls:
   - **Speed Slider**: Control train speed (0-31)
   - **Quick Speed Buttons**: Stop, Slow, Medium, Fast
   - **Direction**: Forward, Reverse, or Toggle
   - **Horn**: Blow the train horn
   - **Bell**: Turn bell on/off
   - **Emergency Stop**: Stop the train immediately
4. **Leave Queue**: Click "Leave Queue" when done

### For Administrators

- **Configure Queue Time**: Adjust the time limit per user in the configuration section
- **Monitor Status**: View real-time queue and train status
- **Emergency Stop**: Available to all users in the queue

## API Endpoints

### Queue Management
- `POST /queue/join` - Join the queue
- `POST /queue/leave` - Leave the queue
- `GET /queue/status` - Get current queue status

### Train Control
- `POST /train/speed` - Set train speed (0-31)
- `POST /train/direction` - Set direction (forward/reverse/toggle)
- `POST /train/horn` - Blow horn
- `POST /train/bell` - Control bell (on/off)
- `POST /train/emergency-stop` - Emergency stop
- `GET /train/status` - Get train status

### Configuration
- `GET /config` - Get current configuration
- `POST /config` - Update configuration

### WebSocket
- `WS /ws` - Real-time queue and train updates

Full API documentation available at: http://localhost:8000/docs

## Development

### Running Without Docker

#### API Service

```bash
cd api
pip install -r requirements.txt
pip install git+https://github.com/chrcraven/pyLionChief.git
python -m uvicorn api.main:app --reload
```

#### UI Service

```bash
cd ui
pip install -r requirements.txt
python app.py
```

### Project Structure

```
LionchiefInteractiveDisplay/
├── api/
│   ├── main.py              # FastAPI application
│   ├── queue_manager.py     # Queue management logic
│   ├── train_controller.py  # Train control interface
│   ├── config.py            # Configuration management
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # API Docker image
├── ui/
│   ├── app.py               # Flask application
│   ├── templates/
│   │   └── index.html       # Main UI template
│   ├── static/
│   │   ├── style.css        # UI styling
│   │   └── app.js           # Client-side logic
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # UI Docker image
├── docker-compose.yml       # Docker Compose configuration
├── .env.example             # Example environment variables
└── README.md                # This file
```

## Troubleshooting

### Train Not Connecting

1. Verify Bluetooth is enabled on your Raspberry Pi
2. Check the train's Bluetooth address in `.env`
3. Ensure the train is powered on and in range
4. Check container logs: `docker-compose logs api`

### Mock Mode

If you want to test without a physical train, leave `TRAIN_ADDRESS` empty in `.env`. The system will run in mock mode.

### WebSocket Connection Issues

- Ensure your firewall allows WebSocket connections
- Check that port 8000 is accessible
- Verify the `API_URL` in `.env` is correct

### Bluetooth Permissions

On Raspberry Pi, ensure the Docker container has Bluetooth access:

```bash
sudo usermod -aG bluetooth $USER
# Restart Docker
sudo systemctl restart docker
```

## License

This project uses pyLionChief for train communication. Please refer to the pyLionChief repository for its license terms.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgments

- Built with [pyLionChief](https://github.com/chrcraven/pyLionChief)
- Uses FastAPI, Flask, and modern web technologies
- Designed for Raspberry Pi deployment
