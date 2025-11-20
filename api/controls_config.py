"""Control configuration management."""
import json
import os
from typing import Dict
import logging

logger = logging.getLogger(__name__)

# Default control settings
DEFAULT_CONTROLS = {
    "speed": True,
    "direction": True,
    "horn": True,
    "bell": True,
    "emergency_stop_all": False,  # False means only current controller + admin
}

CONFIG_FILE = "controls_config.json"


class ControlsConfig:
    """Manages which train controls are available to users."""

    def __init__(self):
        self.controls = self._load_config()
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")  # Empty means no password needed

    def _load_config(self) -> Dict[str, bool]:
        """Load control configuration from file."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    config = DEFAULT_CONTROLS.copy()
                    config.update(data)
                    logger.info(f"Loaded control configuration from {CONFIG_FILE}")
                    return config
        except Exception as e:
            logger.error(f"Error loading control config: {e}")

        logger.info("Using default control configuration")
        return DEFAULT_CONTROLS.copy()

    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.controls, f, indent=2)
            logger.info(f"Saved control configuration to {CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error saving control config: {e}")
            return False

    def is_enabled(self, control_name: str) -> bool:
        """Check if a control is enabled."""
        return self.controls.get(control_name, False)

    def enable_control(self, control_name: str) -> bool:
        """Enable a control."""
        if control_name in DEFAULT_CONTROLS:
            self.controls[control_name] = True
            return self.save_config()
        return False

    def disable_control(self, control_name: str) -> bool:
        """Disable a control."""
        if control_name in DEFAULT_CONTROLS:
            self.controls[control_name] = False
            return self.save_config()
        return False

    def update_controls(self, updates: Dict[str, bool]) -> bool:
        """Update multiple controls at once."""
        for key, value in updates.items():
            if key in DEFAULT_CONTROLS:
                self.controls[key] = value
        return self.save_config()

    def get_all_controls(self) -> Dict[str, bool]:
        """Get all control settings."""
        return self.controls.copy()

    def is_admin(self, password: str) -> bool:
        """Check if password matches admin password."""
        # If no admin password is set, no password is needed
        if not self.admin_password:
            return True
        return password == self.admin_password


# Global instance
controls_config = ControlsConfig()
