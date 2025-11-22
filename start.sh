#!/bin/bash
# Quick start script for LionChief Interactive Display

echo "🚂 LionChief Interactive Display - Starting..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✓ Created .env file. Please edit it to set your train's Bluetooth address."
    echo "  Run: nano .env"
    echo ""
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting services..."
docker-compose up -d

echo ""
echo "✓ Services started successfully!"
echo ""
echo "📍 Access points:"
echo "  - Web UI:  http://localhost:5000"
echo "  - API:     http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "📝 To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "🛑 To stop services:"
echo "  docker-compose down"
echo ""
