"""Train controller interface using pyLionChief."""
import asyncio
from typing import Optional, Dict, List
import logging
import time

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
        self._connection_task: Optional[asyncio.Task] = None
        self._should_reconnect = True
        self._last_command_time = 0  # Track when we last sent a command
        self._disconnect_detected = False  # Flag for voluntary disconnects

    async def initialize(self):
        """Initialize connection to the train with automatic retry."""
        # Check if pyLionChief is available
        try:
            from lionchief.connection import LionChiefConnection
        except ImportError:
            logger.warning("pyLionChief not available, running in mock mode")
            self.train = None
            return

        # Start the connection retry loop in the background
        self._connection_task = asyncio.create_task(self._connection_loop())
        logger.info("Train connection manager started")

    async def _connection_loop(self):
        """Continuously try to connect to the train and maintain connection health."""
        base_retry_delay = 30  # base seconds between retry attempts
        max_retry_delay = 120  # maximum retry delay
        current_retry_delay = base_retry_delay
        health_check_interval = 15  # seconds between health checks when connected
        keepalive_interval = 25  # seconds between keepalive messages
        activity_timeout = 300  # 5 minutes - stop keepalive after this much inactivity

        last_keepalive = 0
        consecutive_failures = 0

        while self._should_reconnect:
            if not self.connected:
                # Clean up any existing connection before reconnecting
                if self.train:
                    try:
                        await self.train.disconnect()
                    except Exception:
                        pass
                    self.train = None

                try:
                    await self._attempt_connection()
                    consecutive_failures = 0
                    current_retry_delay = base_retry_delay
                    last_keepalive = time.time()  # Reset keepalive timer on successful connection
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"Connection attempt failed (attempt {consecutive_failures}): {e}")

                    # Exponential backoff with cap
                    current_retry_delay = min(base_retry_delay * (1.5 ** min(consecutive_failures - 1, 3)), max_retry_delay)
                    logger.info(f"Will retry in {current_retry_delay:.1f} seconds...")

            # Wait before next check
            if not self.connected:
                await asyncio.sleep(current_retry_delay)
            else:
                # Check connection health more frequently when connected
                await asyncio.sleep(health_check_interval)

                # Check if connection is still alive
                if self.train and self.connected:
                    try:
                        # Check the actual BLE connection status
                        if hasattr(self.train, 'train') and hasattr(self.train.train, 'is_connected'):
                            if not self.train.train.is_connected:
                                logger.warning("BLE connection lost (train voluntarily disconnected)")
                                self.connected = False
                                self._disconnect_detected = True
                                self.train = None
                                continue

                        current_time = time.time()
                        time_since_last_command = current_time - self._last_command_time

                        # Only send keepalive if there was recent user activity
                        # This prevents keepalive from affecting train state (like lights) during idle periods
                        if time_since_last_command < activity_timeout:
                            if current_time - last_keepalive > keepalive_interval:
                                # Send keepalive only if train is moving (speed > 0)
                                # This prevents waking up stopped trains and affecting lights/state
                                if self._current_speed > 0:
                                    await self.train.motor.set_speed(int((self._current_speed / 31) * 100))
                                    logger.debug(f"Keepalive sent (speed={self._current_speed})")
                                    last_keepalive = current_time
                        else:
                            # No recent activity - allow train to disconnect naturally
                            # We'll reconnect on the next command
                            logger.debug(f"No activity for {int(time_since_last_command)}s, allowing natural disconnect")

                    except Exception as e:
                        logger.warning(f"Connection health check failed: {e}, will attempt reconnect")
                        self.connected = False
                        self._disconnect_detected = True
                        self.train = None

    def _on_disconnect_callback(self, client):
        """Callback when BLE connection is lost."""
        logger.warning(f"BLE disconnection detected for {client.address}")
        self.connected = False
        # The connection loop will automatically attempt to reconnect

    async def _attempt_connection(self):
        """Attempt to connect to a train (either specified address or discovered)."""
        try:
            from lionchief.connection import LionChiefConnection
        except ImportError:
            logger.error("pyLionChief not available")
            return

        try:
            if self.train_address:
                # Connect to specified address
                logger.info(f"Attempting to connect to train at {self.train_address}...")
                # LionChiefConnection expects (profile, manufacturer_data)
                # For direct connection, we use address as profile and empty dict for manufacturer_data
                self.train = LionChiefConnection(self.train_address, {})
                await self.train.connect()

                # Register disconnect callback if possible
                if hasattr(self.train, 'train') and hasattr(self.train.train, 'set_disconnected_callback'):
                    self.train.train.set_disconnected_callback(self._on_disconnect_callback)
                    logger.debug("Disconnect callback registered")

                self.connected = True
                logger.info(f"✓ Successfully connected to train at {self.train_address}")
            else:
                # Discover and connect to first available
                logger.info("No train address specified, scanning for trains...")
                discovered = await self.scan_for_trains()

                if discovered:
                    first_train = discovered[0]
                    logger.info(f"Found train: {first_train['name']} ({first_train['address']})")
                    logger.info(f"Attempting to connect...")

                    self.train_address = first_train['address']
                    # discovered trains are already LionChiefConnection objects
                    self.train = first_train['connection']
                    await self.train.connect()

                    # Register disconnect callback if possible
                    if hasattr(self.train, 'train') and hasattr(self.train.train, 'set_disconnected_callback'):
                        self.train.train.set_disconnected_callback(self._on_disconnect_callback)
                        logger.debug("Disconnect callback registered")

                    self.connected = True
                    logger.info(f"✓ Successfully connected to {first_train['name']}")
                else:
                    logger.warning("No trains discovered during scan")

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.train = None
            self.connected = False
            raise

    async def stop_connection_manager(self):
        """Stop the connection retry loop."""
        self._should_reconnect = False
        if self._connection_task and not self._connection_task.done():
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass
        logger.info("Train connection manager stopped")

    def _verify_connection(self) -> bool:
        """
        Verify the connection is actually alive.
        Returns True if connected, False otherwise.
        Updates self.connected if connection is actually lost.
        """
        if not self.connected or not self.train:
            return False

        # Check actual BLE connection status
        try:
            if hasattr(self.train, 'train') and hasattr(self.train.train, 'is_connected'):
                if not self.train.train.is_connected:
                    logger.warning("Connection verification failed: BLE not connected")
                    self.connected = False
                    return False
            return True
        except Exception as e:
            logger.warning(f"Connection verification failed: {e}")
            self.connected = False
            return False

    async def set_speed(self, speed: int) -> Dict:
        """Set train speed (0-31)."""
        async with self._lock:
            try:
                if speed < 0 or speed > 31:
                    return {"success": False, "message": "Speed must be between 0 and 31"}

                # Track user activity
                self._last_command_time = time.time()

                # Verify connection before sending command
                if self._verify_connection():
                    # Convert from 0-31 scale to 0-100 scale for lionchief
                    lionchief_speed = int((speed / 31) * 100)
                    await self.train.motor.set_speed(lionchief_speed)
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
                self.connected = False  # Mark as disconnected on error
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

                # Track user activity
                self._last_command_time = time.time()

                # Verify connection before sending command
                if self._verify_connection():
                    if direction == "toggle":
                        new_direction = "reverse" if self._current_direction == "forward" else "forward"
                        await self.train.motor.set_movement_direction(new_direction == "forward")
                        self._current_direction = new_direction
                    elif direction == "forward":
                        await self.train.motor.set_movement_direction(True)
                        self._current_direction = "forward"
                    else:  # reverse
                        await self.train.motor.set_movement_direction(False)
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
                self.connected = False  # Mark as disconnected on error
                return {"success": False, "message": str(e)}

    async def blow_horn(self) -> Dict:
        """Blow the train horn."""
        async with self._lock:
            try:
                # Track user activity
                self._last_command_time = time.time()

                # Verify connection before sending command
                if self._verify_connection():
                    # Turn horn on briefly then off
                    await self.train.sound.set_horn(True)
                    await asyncio.sleep(0.5)
                    await self.train.sound.set_horn(False)
                else:
                    logger.info("Mock: Blowing horn")

                return {"success": True, "message": "Horn blown"}
            except Exception as e:
                logger.error(f"Error blowing horn: {e}")
                self.connected = False  # Mark as disconnected on error
                return {"success": False, "message": str(e)}

    async def ring_bell(self, state: bool) -> Dict:
        """Ring the train bell."""
        async with self._lock:
            try:
                # Track user activity
                self._last_command_time = time.time()

                # Verify connection before sending command
                if self._verify_connection():
                    await self.train.sound.set_bell(state)
                else:
                    logger.info(f"Mock: Bell {'on' if state else 'off'}")

                return {
                    "success": True,
                    "message": f"Bell {'on' if state else 'off'}",
                    "bell_state": state
                }
            except Exception as e:
                logger.error(f"Error controlling bell: {e}")
                self.connected = False  # Mark as disconnected on error
                return {"success": False, "message": str(e)}

    async def set_lights(self, state: bool) -> Dict:
        """Control the train lights."""
        async with self._lock:
            try:
                # Track user activity
                self._last_command_time = time.time()

                # Verify connection before sending command
                if self._verify_connection():
                    await self.train.lighting.set_lights(state)
                else:
                    logger.info(f"Mock: Lights {'on' if state else 'off'}")

                return {
                    "success": True,
                    "message": f"Lights {'on' if state else 'off'}",
                    "lights_state": state
                }
            except Exception as e:
                logger.error(f"Error controlling lights: {e}")
                self.connected = False  # Mark as disconnected on error
                return {"success": False, "message": str(e)}

    async def emergency_stop(self) -> Dict:
        """Emergency stop the train."""
        async with self._lock:
            try:
                # Track user activity
                self._last_command_time = time.time()

                # Verify connection before sending command
                if self._verify_connection():
                    await self.train.motor.stop()
                else:
                    logger.info("Mock: Emergency stop")

                self._current_speed = 0
                return {"success": True, "message": "Emergency stop activated"}
            except Exception as e:
                logger.error(f"Error during emergency stop: {e}")
                self.connected = False  # Mark as disconnected on error
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
                from lionchief.connection import discover_trains
            except ImportError:
                logger.error("pyLionChief not available for train discovery")
                self._scanning = False
                return []

            logger.info(f"Starting train discovery scan...")

            # Use pyLionChief's discover_trains function with retry enabled
            discovered_connections = await discover_trains(retry=True, max_retries=5)

            # Convert to our format
            for connection in discovered_connections:
                # lionchief returns LionChiefConnection objects
                # The profile field contains the BLE device with address
                train_info = {
                    "address": str(connection.profile.address) if hasattr(connection.profile, 'address') else str(connection.profile),
                    "name": connection.profile.name if hasattr(connection.profile, 'name') else 'LionChief Train',
                    "type": "LionChief Train",
                    "connection": connection  # Store the connection object for later use
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
                    from lionchief.connection import LionChiefConnection
                except ImportError:
                    return {
                        "success": False,
                        "message": "pyLionChief not available"
                    }

                logger.info(f"Connecting to train at {address}")
                self.train_address = address
                self.train = LionChiefConnection(address, {})
                await self.train.connect()

                # Register disconnect callback if possible
                if hasattr(self.train, 'train') and hasattr(self.train.train, 'set_disconnected_callback'):
                    self.train.train.set_disconnected_callback(self._on_disconnect_callback)
                    logger.debug("Disconnect callback registered")

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
                    await self.train.disconnect()
                    self.connected = False
                    logger.info("Train disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting from train: {e}")
