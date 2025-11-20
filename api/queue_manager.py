"""Queue management for train control."""
import asyncio
import time
from typing import Dict, List, Optional
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

    def __init__(self, queue_timeout: int = 300, allow_infinite_single: bool = True):
        self.queue_timeout = queue_timeout
        self.allow_infinite_single = allow_infinite_single
        self.queue: List[QueueUser] = []
        self.current_controller: Optional[QueueUser] = None
        self._lock = asyncio.Lock()
        self._timer_task: Optional[asyncio.Task] = None
        self._callbacks: List = []

    def register_callback(self, callback):
        """Register a callback for queue changes."""
        self._callbacks.append(callback)

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

            for i, user in enumerate(self.queue):
                if user.user_id == user_id:
                    user_index = i
                    was_controlling = user.is_active
                    break

            if user_index is None:
                return {
                    "success": False,
                    "message": "User not in queue"
                }

            self.queue.pop(user_index)

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

        # Cancel existing timer
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()

        # Start timer if there are other users waiting
        if len(self.queue) > 1:
            self._timer_task = asyncio.create_task(self._control_timer())

    async def _control_timer(self):
        """Timer to rotate control."""
        try:
            await asyncio.sleep(self.queue_timeout)
            await self._rotate_control()
        except asyncio.CancelledError:
            pass

    async def _rotate_control(self):
        """Rotate control to the next user in queue."""
        async with self._lock:
            if not self.current_controller or not self.queue:
                return

            # Find current controller in queue
            current_index = None
            for i, user in enumerate(self.queue):
                if user.user_id == self.current_controller.user_id:
                    current_index = i
                    user.is_active = False
                    break

            if current_index is not None:
                # Move current controller to end of queue
                user = self.queue.pop(current_index)
                self.queue.append(user)

            # Assign control to next user
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
                # If only one user and infinite mode is enabled
                if len(self.queue) == 1 and self.allow_infinite_single:
                    time_remaining = -1  # Infinite
                else:
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
