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
from api.controls_config import controls_config
from api.analytics import analytics
from api.profanity_filter import profanity_filter
from api.job_scheduler import JobScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
queue_manager: Optional[QueueManager] = None
train_controller: Optional[TrainController] = None
job_scheduler: Optional[JobScheduler] = None
websocket_connections: list[WebSocket] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global queue_manager, train_controller, job_scheduler

    # Startup
    logger.info("Starting train queue system...")

    # Initialize train controller first
    train_controller = TrainController(train_address=config.train_address)
    await train_controller.initialize()

    # Initialize queue manager with train controller reference
    queue_manager = QueueManager(
        queue_timeout=config.queue_timeout,
        allow_infinite_single=config.allow_infinite_single_user,
        idle_timeout=config.idle_timeout,
        train_controller=train_controller
    )

    # Initialize job scheduler
    job_scheduler = JobScheduler(train_controller)
    await job_scheduler.start()

    # Register callback for queue changes
    queue_manager.register_callback(broadcast_queue_status)

    # Register analytics callback
    def analytics_callback(event_type: str, *args):
        if event_type == "start_session":
            analytics.start_session(*args)
        elif event_type == "end_session":
            analytics.end_session(*args)

    queue_manager.register_analytics_callback(analytics_callback)

    logger.info("Train queue system started successfully")

    yield

    # Shutdown
    logger.info("Shutting down train queue system...")
    if queue_manager:
        await queue_manager.stop_idle_timer()
    if job_scheduler:
        await job_scheduler.stop()
    if train_controller:
        await train_controller.stop_connection_manager()
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
    admin_password: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    queue_timeout: Optional[int] = None


class ControlsUpdateRequest(BaseModel):
    admin_password: str
    controls: dict


class CreateJobRequest(BaseModel):
    name: str
    description: str
    script: str
    cron_expression: str
    enabled: bool = True


class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    script: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None


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

    # Check for profanity in username using online API
    contains_profanity, matched_word = await profanity_filter.contains_profanity(request.username)
    if contains_profanity:
        raise HTTPException(
            status_code=400,
            detail=f"Username contains inappropriate language. Please choose a different name."
        )

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

    # Check if speed control is enabled
    if not controls_config.is_enabled("speed"):
        raise HTTPException(status_code=403, detail="Speed control is disabled")

    # Check if user has control
    if not queue_manager.has_control(request.user_id):
        raise HTTPException(status_code=403, detail="You do not have control")

    result = await train_controller.set_speed(request.speed)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Track control usage
    analytics.track_control_usage(request.user_id, "speed")

    return result


@app.post("/train/direction")
async def set_train_direction(request: TrainDirectionRequest):
    """Set train direction."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Check if direction control is enabled
    if not controls_config.is_enabled("direction"):
        raise HTTPException(status_code=403, detail="Direction control is disabled")

    # Check if user has control
    if not queue_manager.has_control(request.user_id):
        raise HTTPException(status_code=403, detail="You do not have control")

    result = await train_controller.set_direction(request.direction)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Track control usage
    analytics.track_control_usage(request.user_id, "direction")

    return result


@app.post("/train/horn")
async def blow_horn(request: TrainHornRequest):
    """Blow the train horn."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Check if horn control is enabled
    if not controls_config.is_enabled("horn"):
        raise HTTPException(status_code=403, detail="Horn control is disabled")

    # Check if user has control
    if not queue_manager.has_control(request.user_id):
        raise HTTPException(status_code=403, detail="You do not have control")

    result = await train_controller.blow_horn()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Track control usage
    analytics.track_control_usage(request.user_id, "horn")

    return result


@app.post("/train/bell")
async def control_bell(request: TrainBellRequest):
    """Control the train bell."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Check if bell control is enabled
    if not controls_config.is_enabled("bell"):
        raise HTTPException(status_code=403, detail="Bell control is disabled")

    # Check if user has control
    if not queue_manager.has_control(request.user_id):
        raise HTTPException(status_code=403, detail="You do not have control")

    result = await train_controller.ring_bell(request.state)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Track control usage
    analytics.track_control_usage(request.user_id, "bell")

    return result


@app.post("/train/emergency-stop")
async def emergency_stop(request: EmergencyStopRequest):
    """Emergency stop the train."""
    if not queue_manager or not train_controller:
        raise HTTPException(status_code=500, detail="System not initialized")

    # Check if emergency stop is available to all users or just current controller + admin
    if controls_config.is_enabled("emergency_stop_all"):
        # Anyone in queue can trigger emergency stop
        pass
    else:
        # Only current controller or admin can trigger emergency stop
        has_control = queue_manager.has_control(request.user_id)
        is_admin = controls_config.is_admin(request.admin_password or "")

        if not has_control and not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Emergency stop can only be triggered by the current controller or admin"
            )

    result = await train_controller.emergency_stop()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    # Track control usage
    analytics.track_control_usage(request.user_id, "emergency_stop")

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


@app.get("/controls")
async def get_controls():
    """Get current control settings."""
    return {
        "controls": controls_config.get_all_controls(),
        "requires_admin_password": bool(controls_config.admin_password)
    }


@app.post("/controls")
async def update_controls(request: ControlsUpdateRequest):
    """Update control settings (requires admin password)."""
    # Verify admin password
    if not controls_config.is_admin(request.admin_password):
        raise HTTPException(status_code=403, detail="Invalid admin password")

    # Update controls
    if controls_config.update_controls(request.controls):
        return {
            "success": True,
            "controls": controls_config.get_all_controls()
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to save control settings")


@app.get("/analytics/stats")
async def get_analytics_stats(days: Optional[int] = None):
    """Get analytics statistics."""
    return analytics.get_statistics(days)


@app.get("/analytics/hourly")
async def get_hourly_distribution(days: int = 7):
    """Get hourly session distribution."""
    if days < 1 or days > 90:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 90")

    return {
        "hourly_distribution": analytics.get_hourly_distribution(days),
        "days": days
    }


@app.get("/analytics/controls")
async def get_control_breakdown():
    """Get control usage breakdown."""
    return {
        "control_breakdown": analytics.get_control_breakdown(),
        "total_usage": analytics.data["control_usage"]
    }


@app.delete("/analytics/cleanup")
async def cleanup_old_analytics(days: int = 90):
    """Clean up old analytics data."""
    if days < 7 or days > 365:
        raise HTTPException(status_code=400, detail="Days must be between 7 and 365")

    removed = analytics.clear_old_data(days)
    return {
        "success": True,
        "removed_sessions": removed,
        "message": f"Removed {removed} sessions older than {days} days"
    }


@app.get("/profanity-filter")
async def get_profanity_filter():
    """Get profanity filter settings."""
    return {
        "blocked_words": profanity_filter.get_blocked_words()
    }


@app.post("/profanity-filter/add")
async def add_blocked_word(word: str, admin_password: Optional[str] = None):
    """Add a word to the profanity filter."""
    if not controls_config.is_admin(admin_password or ""):
        raise HTTPException(status_code=403, detail="Admin password required")

    if profanity_filter.add_blocked_word(word):
        return {"success": True, "message": f"Added '{word}' to blocked words"}
    else:
        return {"success": False, "message": "Word already in list or invalid"}


@app.delete("/profanity-filter/remove")
async def remove_blocked_word(word: str, admin_password: Optional[str] = None):
    """Remove a word from the profanity filter."""
    if not controls_config.is_admin(admin_password or ""):
        raise HTTPException(status_code=403, detail="Admin password required")

    if profanity_filter.remove_blocked_word(word):
        return {"success": True, "message": f"Removed '{word}' from blocked words"}
    else:
        return {"success": False, "message": "Word not found in list"}


@app.post("/profanity-filter/reset")
async def reset_profanity_filter(admin_password: Optional[str] = None):
    """Reset profanity filter to defaults."""
    if not controls_config.is_admin(admin_password or ""):
        raise HTTPException(status_code=403, detail="Admin password required")

    if profanity_filter.reset_to_defaults():
        return {"success": True, "message": "Reset to default blocked words"}
    else:
        return {"success": False, "message": "Failed to reset"}


@app.get("/jobs")
async def list_jobs():
    """List all scheduled jobs."""
    if not job_scheduler:
        raise HTTPException(status_code=500, detail="Job scheduler not initialized")

    return {"jobs": job_scheduler.list_jobs()}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Get a specific job."""
    if not job_scheduler:
        raise HTTPException(status_code=500, detail="Job scheduler not initialized")

    job = job_scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"job": job.to_dict()}


@app.post("/jobs")
async def create_job(request: CreateJobRequest, admin_password: Optional[str] = None):
    """Create a new scheduled job."""
    if not controls_config.is_admin(admin_password or ""):
        raise HTTPException(status_code=403, detail="Admin password required")

    if not job_scheduler:
        raise HTTPException(status_code=500, detail="Job scheduler not initialized")

    result = job_scheduler.create_job(
        name=request.name,
        description=request.description,
        script=request.script,
        cron_expression=request.cron_expression,
        enabled=request.enabled
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create job"))

    return result


@app.put("/jobs/{job_id}")
async def update_job(job_id: str, request: UpdateJobRequest, admin_password: Optional[str] = None):
    """Update an existing job."""
    if not controls_config.is_admin(admin_password or ""):
        raise HTTPException(status_code=403, detail="Admin password required")

    if not job_scheduler:
        raise HTTPException(status_code=500, detail="Job scheduler not initialized")

    result = job_scheduler.update_job(
        job_id=job_id,
        name=request.name,
        description=request.description,
        script=request.script,
        cron_expression=request.cron_expression,
        enabled=request.enabled
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to update job"))

    return result


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str, admin_password: Optional[str] = None):
    """Delete a job."""
    if not controls_config.is_admin(admin_password or ""):
        raise HTTPException(status_code=403, detail="Admin password required")

    if not job_scheduler:
        raise HTTPException(status_code=500, detail="Job scheduler not initialized")

    result = job_scheduler.delete_job(job_id)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to delete job"))

    return result


@app.post("/jobs/{job_id}/run")
async def run_job_now(job_id: str, admin_password: Optional[str] = None):
    """Run a job immediately (outside of schedule)."""
    if not controls_config.is_admin(admin_password or ""):
        raise HTTPException(status_code=403, detail="Admin password required")

    if not job_scheduler:
        raise HTTPException(status_code=500, detail="Job scheduler not initialized")

    result = await job_scheduler.run_job_now(job_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to run job"))

    return result


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
