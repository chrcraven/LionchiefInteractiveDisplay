"""Analytics tracking for train queue system."""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

ANALYTICS_FILE = "analytics_data.json"


class AnalyticsTracker:
    """Tracks usage analytics for the train queue system."""

    def __init__(self):
        self.data = self._load_data()
        self.current_sessions = {}  # Track active sessions

    def _load_data(self) -> Dict:
        """Load analytics data from file."""
        try:
            if os.path.exists(ANALYTICS_FILE):
                with open(ANALYTICS_FILE, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded analytics data from {ANALYTICS_FILE}")
                    return data
        except Exception as e:
            logger.error(f"Error loading analytics data: {e}")

        # Initialize with default structure
        return {
            "sessions": [],
            "control_usage": {
                "speed": 0,
                "direction": 0,
                "horn": 0,
                "bell": 0,
                "emergency_stop": 0
            },
            "total_users": 0,
            "total_session_time": 0,
            "total_wait_time": 0
        }

    def _save_data(self) -> bool:
        """Save analytics data to file."""
        try:
            with open(ANALYTICS_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}")
            return False

    def start_session(self, user_id: str, username: str, queue_join_time: float):
        """Record the start of a control session."""
        session_start = datetime.now().isoformat()
        wait_time = datetime.now().timestamp() - queue_join_time

        self.current_sessions[user_id] = {
            "username": username,
            "queue_join_time": queue_join_time,
            "session_start": session_start,
            "session_start_timestamp": datetime.now().timestamp(),
            "wait_time": wait_time,
            "controls_used": {
                "speed": 0,
                "direction": 0,
                "horn": 0,
                "bell": 0,
                "emergency_stop": 0
            }
        }

        logger.info(f"Started session for user {username} (waited {wait_time:.1f}s)")

    def end_session(self, user_id: str):
        """Record the end of a control session."""
        if user_id not in self.current_sessions:
            return

        session = self.current_sessions[user_id]
        session_end = datetime.now().isoformat()
        session_duration = datetime.now().timestamp() - session["session_start_timestamp"]

        # Create session record
        session_record = {
            "username": session["username"],
            "queue_join_time": datetime.fromtimestamp(session["queue_join_time"]).isoformat(),
            "session_start": session["session_start"],
            "session_end": session_end,
            "wait_time": session["wait_time"],
            "session_duration": session_duration,
            "controls_used": session["controls_used"]
        }

        # Add to sessions list
        self.data["sessions"].append(session_record)

        # Update totals
        self.data["total_users"] += 1
        self.data["total_session_time"] += session_duration
        self.data["total_wait_time"] += session["wait_time"]

        # Update control usage totals
        for control, count in session["controls_used"].items():
            self.data["control_usage"][control] += count

        # Remove from current sessions
        del self.current_sessions[user_id]

        # Save data
        self._save_data()

        logger.info(f"Ended session for {session['username']} (duration: {session_duration:.1f}s)")

    def track_control_usage(self, user_id: str, control_type: str):
        """Track usage of a control."""
        if user_id in self.current_sessions:
            self.current_sessions[user_id]["controls_used"][control_type] += 1

    def get_statistics(self, days: Optional[int] = None) -> Dict:
        """Get analytics statistics."""
        sessions = self.data["sessions"]

        # Filter by date if specified
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            sessions = [
                s for s in sessions
                if datetime.fromisoformat(s["session_start"]) >= cutoff
            ]

        if not sessions:
            return {
                "total_sessions": 0,
                "total_users": 0,
                "avg_wait_time": 0,
                "avg_session_duration": 0,
                "total_control_usage": self.data["control_usage"],
                "peak_hours": {},
                "busiest_day": None
            }

        # Calculate statistics
        total_sessions = len(sessions)
        avg_wait_time = sum(s["wait_time"] for s in sessions) / total_sessions
        avg_session_duration = sum(s["session_duration"] for s in sessions) / total_sessions

        # Peak hours analysis
        hours_count = defaultdict(int)
        for session in sessions:
            hour = datetime.fromisoformat(session["session_start"]).hour
            hours_count[hour] += 1

        peak_hours = dict(sorted(hours_count.items(), key=lambda x: x[1], reverse=True)[:5])

        # Busiest day analysis
        days_count = defaultdict(int)
        for session in sessions:
            day = datetime.fromisoformat(session["session_start"]).strftime("%Y-%m-%d")
            days_count[day] += 1

        busiest_day = max(days_count.items(), key=lambda x: x[1]) if days_count else None

        # Day of week analysis
        weekday_count = defaultdict(int)
        for session in sessions:
            weekday = datetime.fromisoformat(session["session_start"]).strftime("%A")
            weekday_count[weekday] += 1

        # Most active users
        user_count = defaultdict(int)
        for session in sessions:
            user_count[session["username"]] += 1

        top_users = dict(sorted(user_count.items(), key=lambda x: x[1], reverse=True)[:10])

        return {
            "total_sessions": total_sessions,
            "total_users": len(user_count),
            "avg_wait_time": round(avg_wait_time, 2),
            "avg_session_duration": round(avg_session_duration, 2),
            "total_control_usage": self.data["control_usage"],
            "peak_hours": peak_hours,
            "busiest_day": busiest_day,
            "weekday_distribution": dict(weekday_count),
            "top_users": top_users,
            "recent_sessions": sessions[-10:]  # Last 10 sessions
        }

    def get_hourly_distribution(self, days: int = 7) -> Dict[int, int]:
        """Get session distribution by hour of day."""
        cutoff = datetime.now() - timedelta(days=days)
        hours_count = defaultdict(int)

        for session in self.data["sessions"]:
            session_time = datetime.fromisoformat(session["session_start"])
            if session_time >= cutoff:
                hours_count[session_time.hour] += 1

        return dict(hours_count)

    def get_control_breakdown(self) -> Dict:
        """Get detailed control usage breakdown."""
        total = sum(self.data["control_usage"].values())
        if total == 0:
            return self.data["control_usage"]

        breakdown = {}
        for control, count in self.data["control_usage"].items():
            breakdown[control] = {
                "count": count,
                "percentage": round((count / total) * 100, 1)
            }

        return breakdown

    def clear_old_data(self, days: int = 90):
        """Clear analytics data older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)

        original_count = len(self.data["sessions"])
        self.data["sessions"] = [
            s for s in self.data["sessions"]
            if datetime.fromisoformat(s["session_start"]) >= cutoff
        ]

        removed = original_count - len(self.data["sessions"])
        if removed > 0:
            self._save_data()
            logger.info(f"Cleared {removed} old session records")

        return removed


# Global analytics instance
analytics = AnalyticsTracker()
