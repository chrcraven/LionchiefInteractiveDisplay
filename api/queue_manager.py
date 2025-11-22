"""Queue management for train control."""
import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QueueUser:
    """Represents a user in the queue."""
    user_id: str
    username: str
    joined_at: float
    control_started_at: Optional[float] = None
    is_active: bool = False


class QueueManager:
    """Manages the queue for train control."""

    def __init__(self, queue_timeout: int = 60,
                 idle_timeout: int = 600, train_controller=None):
        self.queue_timeout = queue_timeout
        self.idle_timeout = idle_timeout  # Time in seconds before turning off lights when idle
        self.train_controller = train_controller
        self.queue: List[QueueUser] = []
        self.current_controller: Optional[QueueUser] = None
        self._lock = asyncio.Lock()
        self._timer_task: Optional[asyncio.Task] = None
        self._idle_timer_task: Optional[asyncio.Task] = None
        self._last_activity_time: float = time.time()
        self._lights_auto_off: bool = False  # Track if lights were auto-turned off
        self._callbacks: List = []
        self._analytics_callback: Optional[Callable] = None

        # Start idle timer
        if self.train_controller and self.idle_timeout > 0:
            self._start_idle_timer()

    def register_callback(self, callback):
        """Register a callback for queue changes."""
        self._callbacks.append(callback)

    def register_analytics_callback(self, callback):
        """Register analytics tracking callback."""
        self._analytics_callback = callback

    async def _notify_callbacks(self):
        """Notify all registered callbacks of queue changes."""
        for callback in self._callbacks:
            try:
                await callback()
            except Exception as e:
                print(f"Error in callback: {e}")

    async def join_queue(self, user_id: str, username: str) -> Dict:
        """Add a user to the queue."""
        async with self._lock:
            # Check if user already in queue
            for user in self.queue:
                if user.user_id == user_id:
                    return {
                        "success": False,
                        "message": "User already in queue",
                        "position": self.queue.index(user) + 1
                    }

            user = QueueUser(
                user_id=user_id,
                username=username,
                joined_at=time.time()
            )

            self.queue.append(user)

            # Update activity time
            self._update_activity_time()

            # If this is the first user, give them control immediately
            if len(self.queue) == 1 and self.current_controller is None:
                await self._assign_control(user)

            await self._notify_callbacks()

            return {
                "success": True,
                "message": "Added to queue",
                "position": len(self.queue),
                "queue_length": len(self.queue)
            }

    async def leave_queue(self, user_id: str) -> Dict:
        """Remove a user from the queue."""
        async with self._lock:
            user_index = None
            was_controlling = False
            user_obj = None

            for i, user in enumerate(self.queue):
                if user.user_id == user_id:
                    user_index = i
                    was_controlling = user.is_active
                    user_obj = user
                    break

            if user_index is None:
                return {
                    "success": False,
                    "message": "User not in queue"
                }

            self.queue.pop(user_index)

            # Update activity time
            self._update_activity_time()

            # Notify analytics if user was controlling
            if was_controlling and self._analytics_callback and user_obj:
                try:
                    self._analytics_callback("end_session", user_id)
                except Exception as e:
                    print(f"Error in analytics callback: {e}")

            # Clean up train state if user was controlling
            if was_controlling and self.train_controller:
                try:
                    await self.train_controller.end_session_cleanup()
                except Exception as e:
                    print(f"Error during session cleanup: {e}")

            # If the leaving user was controlling, assign to next
            if was_controlling:
                self.current_controller = None
                if self.queue:
                    await self._assign_control(self.queue[0])

            await self._notify_callbacks()

            return {
                "success": True,
                "message": "Removed from queue"
            }

    async def _assign_control(self, user: QueueUser):
        """Assign control to a user."""
        user.is_active = True
        user.control_started_at = time.time()
        self.current_controller = user

        # Notify analytics
        if self._analytics_callback:
            try:
                self._analytics_callback("start_session", user.user_id, user.username, user.joined_at)
            except Exception as e:
                print(f"Error in analytics callback: {e}")

        # Cancel existing timer
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()

        # Always start timer - users must rejoin queue after timeout
        self._timer_task = asyncio.create_task(self._control_timer())

    async def _control_timer(self):
        """Timer to rotate control."""
        try:
            await asyncio.sleep(self.queue_timeout)
            await self._rotate_control()
        except asyncio.CancelledError:
            pass

    async def _rotate_control(self):
        """Remove current user from queue after timeout and assign control to next user."""
        async with self._lock:
            if not self.current_controller or not self.queue:
                return

            # Find current controller in queue
            current_index = None
            removed_user = None
            for i, user in enumerate(self.queue):
                if user.user_id == self.current_controller.user_id:
                    current_index = i
                    removed_user = user
                    break

            # Notify analytics that session is ending
            if removed_user and self._analytics_callback:
                try:
                    self._analytics_callback("end_session", removed_user.user_id)
                except Exception as e:
                    print(f"Error in analytics callback: {e}")

            # Clean up train state before rotating to next user
            if self.train_controller:
                try:
                    await self.train_controller.end_session_cleanup()
                except Exception as e:
                    print(f"Error during session cleanup on rotation: {e}")

            if current_index is not None:
                # Remove current controller from queue - they must rejoin for more time
                self.queue.pop(current_index)
                print(f"User {removed_user.username} session expired, removed from queue")

            # Clear current controller
            self.current_controller = None

            # Assign control to next user if any remain in queue
            if self.queue:
                await self._assign_control(self.queue[0])

            await self._notify_callbacks()

    def get_queue_status(self) -> Dict:
        """Get current queue status."""
        queue_list = []
        for i, user in enumerate(self.queue):
            time_remaining = None
            if user.is_active and user.control_started_at:
                elapsed = time.time() - user.control_started_at
                time_remaining = max(0, self.queue_timeout - elapsed)

            queue_list.append({
                "user_id": user.user_id,
                "username": user.username,
                "position": i + 1,
                "is_active": user.is_active,
                "time_remaining": time_remaining,
                "joined_at": user.joined_at
            })

        return {
            "queue": queue_list,
            "queue_length": len(self.queue),
            "current_controller": self.current_controller.user_id if self.current_controller else None,
            "queue_timeout": self.queue_timeout
        }

    def has_control(self, user_id: str) -> bool:
        """Check if a user has control."""
        return self.current_controller is not None and self.current_controller.user_id == user_id

    async def update_timeout(self, new_timeout: int):
        """Update the queue timeout."""
        async with self._lock:
            self.queue_timeout = new_timeout

            # Restart timer if someone is currently controlling
            if self.current_controller and len(self.queue) > 1:
                if self._timer_task and not self._timer_task.done():
                    self._timer_task.cancel()
                self._timer_task = asyncio.create_task(self._control_timer())

            await self._notify_callbacks()

    def _update_activity_time(self):
        """Update the last activity time to reset idle timer."""
        self._last_activity_time = time.time()
        # Turn lights back on if they were auto-turned off
        if self._lights_auto_off and self.train_controller:
            self._lights_auto_off = False
            asyncio.create_task(self._turn_lights_on())

    async def _turn_lights_on(self):
        """Turn lights back on after activity."""
        try:
            await self.train_controller.set_lights(True)
        except Exception as e:
            print(f"Error turning lights on: {e}")

    def _start_idle_timer(self):
        """Start the idle timeout timer."""
        if self._idle_timer_task is None or self._idle_timer_task.done():
            self._idle_timer_task = asyncio.create_task(self._idle_timer_loop())

    async def _idle_timer_loop(self):
        """Monitor for idle timeout and turn off lights when idle."""
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Only check if queue is empty
                if len(self.queue) == 0:
                    idle_time = time.time() - self._last_activity_time

                    # If idle for longer than timeout and lights haven't been turned off yet
                    if idle_time >= self.idle_timeout and not self._lights_auto_off:
                        print(f"Queue idle for {idle_time:.0f}s, turning off lights")
                        await self._turn_lights_off_idle()
                else:
                    # Queue has activity, update last activity time
                    self._update_activity_time()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error in idle timer loop: {e}")

    async def _turn_lights_off_idle(self):
        """Turn off lights due to idle timeout."""
        if self.train_controller:
            try:
                result = await self.train_controller.set_lights(False)
                if result.get("success"):
                    self._lights_auto_off = True
                    print("Lights automatically turned off due to inactivity")
            except Exception as e:
                print(f"Error turning off lights: {e}")

    async def stop_idle_timer(self):
        """Stop the idle timeout timer."""
        if self._idle_timer_task and not self._idle_timer_task.done():
            self._idle_timer_task.cancel()
            try:
                await self._idle_timer_task
            except asyncio.CancelledError:
                pass
