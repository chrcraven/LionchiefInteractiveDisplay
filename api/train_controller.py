"""Train controller interface using pyLionChief."""
import asyncio
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class TrainController:
    """Controls the LionChief train."""

    def __init__(self, train_address: Optional[str] = None):
        self.train_address = train_address
        self.train = None
        self.connected = False
        self._lock = asyncio.Lock()
        self._current_speed = 0
        self._current_direction = "forward"

    async def initialize(self):
        """Initialize connection to the train."""
        try:
            # Import pyLionChief - try both possible import paths
            try:
                from pyLionChief import LionChiefEngine
            except ImportError:
                try:
                    from pyLionChief.pyLionChief import LionChiefEngine
                except ImportError:
                    logger.warning("pyLionChief not available, running in mock mode")
                    self.train = None
                    return

            if self.train_address:
                logger.info(f"Connecting to train at {self.train_address}")
                self.train = LionChiefEngine(self.train_address)
                await asyncio.to_thread(self.train.connect)
                self.connected = True
                logger.info("Train connected successfully")
            else:
                logger.warning("No train address configured, running in mock mode")
                self.train = None

        except Exception as e:
            logger.error(f"Error initializing train: {e}")
            self.train = None
            self.connected = False

    async def set_speed(self, speed: int) -> Dict:
        """Set train speed (0-31)."""
        async with self._lock:
            try:
                if speed < 0 or speed > 31:
                    return {"success": False, "message": "Speed must be between 0 and 31"}

                if self.train and self.connected:
                    await asyncio.to_thread(self.train.set_speed, speed)
                else:
                    logger.info(f"Mock: Setting speed to {speed}")

                self._current_speed = speed
                return {
                    "success": True,
                    "message": f"Speed set to {speed}",
                    "speed": speed
                }
            except Exception as e:
                logger.error(f"Error setting speed: {e}")
                return {"success": False, "message": str(e)}

    async def set_direction(self, direction: str) -> Dict:
        """Set train direction (forward/reverse/toggle)."""
        async with self._lock:
            try:
                if direction not in ["forward", "reverse", "toggle"]:
                    return {
                        "success": False,
                        "message": "Direction must be 'forward', 'reverse', or 'toggle'"
                    }

                if self.train and self.connected:
                    if direction == "toggle":
                        await asyncio.to_thread(self.train.toggle_direction)
                        self._current_direction = "reverse" if self._current_direction == "forward" else "forward"
                    elif direction == "forward":
                        await asyncio.to_thread(self.train.set_forward)
                        self._current_direction = "forward"
                    else:  # reverse
                        await asyncio.to_thread(self.train.set_reverse)
                        self._current_direction = "reverse"
                else:
                    logger.info(f"Mock: Setting direction to {direction}")
                    if direction == "toggle":
                        self._current_direction = "reverse" if self._current_direction == "forward" else "forward"
                    else:
                        self._current_direction = direction

                return {
                    "success": True,
                    "message": f"Direction set to {self._current_direction}",
                    "direction": self._current_direction
                }
            except Exception as e:
                logger.error(f"Error setting direction: {e}")
                return {"success": False, "message": str(e)}

    async def blow_horn(self) -> Dict:
        """Blow the train horn."""
        async with self._lock:
            try:
                if self.train and self.connected:
                    await asyncio.to_thread(self.train.blow_horn_one)
                else:
                    logger.info("Mock: Blowing horn")

                return {"success": True, "message": "Horn blown"}
            except Exception as e:
                logger.error(f"Error blowing horn: {e}")
                return {"success": False, "message": str(e)}

    async def ring_bell(self, state: bool) -> Dict:
        """Ring the train bell."""
        async with self._lock:
            try:
                if self.train and self.connected:
                    if state:
                        await asyncio.to_thread(self.train.ring_bell)
                    else:
                        await asyncio.to_thread(self.train.stop_bell)
                else:
                    logger.info(f"Mock: Bell {'on' if state else 'off'}")

                return {
                    "success": True,
                    "message": f"Bell {'on' if state else 'off'}",
                    "bell_state": state
                }
            except Exception as e:
                logger.error(f"Error controlling bell: {e}")
                return {"success": False, "message": str(e)}

    async def emergency_stop(self) -> Dict:
        """Emergency stop the train."""
        async with self._lock:
            try:
                if self.train and self.connected:
                    await asyncio.to_thread(self.train.set_speed, 0)
                else:
                    logger.info("Mock: Emergency stop")

                self._current_speed = 0
                return {"success": True, "message": "Emergency stop activated"}
            except Exception as e:
                logger.error(f"Error during emergency stop: {e}")
                return {"success": False, "message": str(e)}

    def get_status(self) -> Dict:
        """Get current train status."""
        return {
            "connected": self.connected,
            "speed": self._current_speed,
            "direction": self._current_direction,
            "mock_mode": self.train is None
        }

    async def disconnect(self):
        """Disconnect from the train."""
        async with self._lock:
            try:
                if self.train and self.connected:
                    await asyncio.to_thread(self.train.disconnect)
                    self.connected = False
                    logger.info("Train disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting from train: {e}")
