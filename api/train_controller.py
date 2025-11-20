"""Train controller interface using pyLionChief."""
import asyncio
from typing import Optional, Dict, List
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
        self._discovered_trains: List[Dict] = []
        self._scanning = False

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
                logger.info("No train address configured, attempting to discover trains...")
                # Try to discover trains
                discovered = await self.scan_for_trains()

                if discovered:
                    # Auto-connect to the first discovered train
                    first_train = discovered[0]
                    logger.info(f"Auto-connecting to discovered train: {first_train['name']} ({first_train['address']})")
                    await self.connect_to_train(first_train['address'])
                else:
                    logger.warning("No trains discovered, running in mock mode")
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
            "mock_mode": self.train is None,
            "train_address": self.train_address,
            "discovered_trains": len(self._discovered_trains)
        }

    async def scan_for_trains(self, scan_duration: int = 10) -> List[Dict]:
        """
        Scan for nearby LionChief trains using pyLionChief's discovery.

        Args:
            scan_duration: How long to scan in seconds (default 10)

        Returns:
            List of discovered trains with name and address
        """
        if self._scanning:
            logger.warning("Scan already in progress")
            return self._discovered_trains

        self._scanning = True
        self._discovered_trains = []

        try:
            # Import pyLionChief discovery
            try:
                from pyLionChief import discover_trains
            except ImportError:
                try:
                    from pyLionChief.pyLionChief import discover_trains
                except ImportError:
                    logger.error("pyLionChief not available for train discovery")
                    self._scanning = False
                    return []

            logger.info(f"Starting train discovery scan for {scan_duration} seconds...")

            # Use pyLionChief's discover_trains function
            discovered_devices = await asyncio.to_thread(discover_trains, scan_duration)

            # Convert to our format
            for device in discovered_devices:
                # pyLionChief returns devices with 'address' and 'name' keys
                train_info = {
                    "address": device.get('address', device.get('addr', 'Unknown')),
                    "name": device.get('name', 'LionChief Train'),
                    "type": "LionChief Train"
                }
                self._discovered_trains.append(train_info)
                logger.info(f"Discovered train: {train_info['name']} ({train_info['address']})")

            if not self._discovered_trains:
                logger.warning("No LionChief trains found during scan")
            else:
                logger.info(f"Found {len(self._discovered_trains)} train(s)")

        except Exception as e:
            logger.error(f"Error during train scanning: {e}")
            logger.info("Train discovery failed - ensure Bluetooth is enabled and you have permissions")
        finally:
            self._scanning = False

        return self._discovered_trains

    def get_discovered_trains(self) -> List[Dict]:
        """Get list of discovered trains."""
        return self._discovered_trains

    def is_scanning(self) -> bool:
        """Check if currently scanning for trains."""
        return self._scanning

    async def connect_to_train(self, address: str) -> Dict:
        """
        Connect to a specific train by address.

        Args:
            address: Bluetooth MAC address of the train

        Returns:
            Dict with success status and message
        """
        async with self._lock:
            try:
                # Disconnect from current train if connected
                if self.connected:
                    await self.disconnect()

                # Import pyLionChief
                try:
                    from pyLionChief import LionChiefEngine
                except ImportError:
                    try:
                        from pyLionChief.pyLionChief import LionChiefEngine
                    except ImportError:
                        return {
                            "success": False,
                            "message": "pyLionChief not available"
                        }

                logger.info(f"Connecting to train at {address}")
                self.train_address = address
                self.train = LionChiefEngine(address)
                await asyncio.to_thread(self.train.connect)
                self.connected = True
                logger.info("Train connected successfully")

                return {
                    "success": True,
                    "message": f"Connected to train at {address}",
                    "address": address
                }

            except Exception as e:
                logger.error(f"Error connecting to train: {e}")
                self.train = None
                self.connected = False
                return {
                    "success": False,
                    "message": f"Failed to connect: {str(e)}"
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
