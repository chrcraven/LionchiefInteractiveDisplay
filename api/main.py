"""Main FastAPI application for train queue system."""
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from api.config import config
from api.queue_manager import QueueManager
from api.train_controller import TrainController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
queue_manager: Optional[QueueManager] = None
train_controller: Optional[TrainController] = None
websocket_connections: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global queue_manager, train_controller

    # Startup
    logger.info("Starting train queue system...")
    queue_manager = QueueManager(
        queue_timeout=config.queue_timeout,
        allow_infinite_single=config.allow_infinite_single_user
    )
    train_controller = TrainController(train_address=config.train_address)
    await train_controller.initialize()

    # Register callback for queue changes
    queue_manager.register_callback(broadcast_queue_status)

    logger.info("Train queue system started successfully")

    yield

    # Shutdown
    logger.info("Shutting down train queue system...")
    if train_controller:
        await train_controller.disconnect()
    logger.info("Train queue system shutdown complete")


app = FastAPI(
    title="LionChief Train Queue API",
    description="API for managing queue-based control of a LionChief train",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class JoinQueueRequest(BaseModel):
    user_id: str
    username: str


class LeaveQueueRequest(BaseModel):
    user_id: str


class TrainSpeedRequest(BaseModel):
    user_id: str
    speed: int


class TrainDirectionRequest(BaseModel):
    user_id: str
    direction: str


class TrainHornRequest(BaseModel):
    user_id: str


class TrainBellRequest(BaseModel):
    user_id: str
    state: bool


class EmergencyStopRequest(BaseModel):
    user_id: str


class ConfigUpdateRequest(BaseModel):
    queue_timeout: Optional[int] = None


# WebSocket broadcast function
async def broadcast_queue_status():
    """Broadcast queue status to all connected websockets."""
    if not queue_manager:
        return

    status = queue_manager.get_queue_status()
    disconnected = []

    for ws in websocket_connections:
        try:
            await ws.send_json({"type": "queue_update", "data": status})
        except Exception as e:
            logger.error(f"Error broadcasting to websocket: {e}")
            disconnected.append(ws)

    # Remove disconnected websockets
    for ws in disconnected:
        if ws in websocket_connections:
            websocket_connections.remove(ws)


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LionChief Train Queue API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/queue/join")
async def join_queue(request: JoinQueueRequest):
    """Join the queue."""
    if not queue_manager:
        raise HTTPException(status_code=500, detail="Queue manager not initialized")

    result = await queue_manager.join_queue(request.user_id, request.username)
    return result


@app.post("/queue/leave")
async def leave_queue(request: LeaveQueueRequest):
    """Leave the queue."""
    if not queue_manager:
        raise HTTPException(status_code=500, detail="Queue manager not initialized")

    result = await queue_manager.leave_queue(request.user_id)
    return result


@app.get("/queue/status")
async def get_queue_status():
    """Get current queue status."""
    if not queue_manager:
        raise HTTPException(status_code=500, detail="Queue manager not initialized")

    return queue_manager.get_queue_status()


@app.post("/train/speed")
async def set_train_speed(request: TrainSpeedRequest):
    """Set train speed."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Check if user has control
    if not queue_manager.has_control(request.user_id):
        raise HTTPException(status_code=403, detail="You do not have control")

    result = await train_controller.set_speed(request.speed)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.post("/train/direction")
async def set_train_direction(request: TrainDirectionRequest):
    """Set train direction."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Check if user has control
    if not queue_manager.has_control(request.user_id):
        raise HTTPException(status_code=403, detail="You do not have control")

    result = await train_controller.set_direction(request.direction)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.post("/train/horn")
async def blow_horn(request: TrainHornRequest):
    """Blow the train horn."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Check if user has control
    if not queue_manager.has_control(request.user_id):
        raise HTTPException(status_code=403, detail="You do not have control")

    result = await train_controller.blow_horn()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.post("/train/bell")
async def control_bell(request: TrainBellRequest):
    """Control the train bell."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Check if user has control
    if not queue_manager.has_control(request.user_id):
        raise HTTPException(status_code=403, detail="You do not have control")

    result = await train_controller.ring_bell(request.state)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.post("/train/emergency-stop")
async def emergency_stop(request: EmergencyStopRequest):
    """Emergency stop the train."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Emergency stop can be triggered by anyone in the queue
    result = await train_controller.emergency_stop()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.get("/train/status")
async def get_train_status():
    """Get train status."""
    if not train_controller:
        raise HTTPException(status_code=500, detail="Train controller not initialized")

    return train_controller.get_status()


@app.get("/train/scan")
async def scan_for_trains(duration: int = 10):
    """
    Scan for nearby LionChief trains.

    Args:
        duration: Scan duration in seconds (default 10, max 30)
    """
    if not train_controller:
        raise HTTPException(status_code=500, detail="Train controller not initialized")

    if duration < 5 or duration > 30:
        raise HTTPException(status_code=400, detail="Duration must be between 5 and 30 seconds")

    if train_controller.is_scanning():
        raise HTTPException(status_code=409, detail="Scan already in progress")

    discovered = await train_controller.scan_for_trains(scan_duration=duration)

    return {
        "success": True,
        "trains": discovered,
        "count": len(discovered)
    }


@app.get("/train/discovered")
async def get_discovered_trains():
    """Get list of previously discovered trains."""
    if not train_controller:
        raise HTTPException(status_code=500, detail="Train controller not initialized")

    trains = train_controller.get_discovered_trains()

    return {
        "trains": trains,
        "count": len(trains),
        "scanning": train_controller.is_scanning()
    }


class ConnectTrainRequest(BaseModel):
    address: str


@app.post("/train/connect")
async def connect_train(request: ConnectTrainRequest):
    """Connect to a specific train by Bluetooth address."""
    if not train_controller:
        raise HTTPException(status_code=500, detail="Train controller not initialized")

    result = await train_controller.connect_to_train(request.address)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@app.get("/config")
async def get_config():
    """Get current configuration."""
    return {
        "queue_timeout": config.queue_timeout,
        "allow_infinite_single_user": config.allow_infinite_single_user,
        "train_address": config.train_address,
    }


@app.post("/config")
async def update_config(request: ConfigUpdateRequest):
    """Update configuration."""
    if not queue_manager:
        raise HTTPException(status_code=500, detail="Queue manager not initialized")

    if request.queue_timeout is not None:
        if request.queue_timeout < 10 or request.queue_timeout > 3600:
            raise HTTPException(
                status_code=400,
                detail="Queue timeout must be between 10 and 3600 seconds"
            )
        config.queue_timeout = request.queue_timeout
        await queue_manager.update_timeout(request.queue_timeout)

    return {"success": True, "config": await get_config()}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    websocket_connections.append(websocket)

    try:
        # Send initial queue status
        if queue_manager:
            status = queue_manager.get_queue_status()
            await websocket.send_json({"type": "queue_update", "data": status})

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong or other messages if needed

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.server_host,
        port=config.server_port,
        log_level="info"
    )
