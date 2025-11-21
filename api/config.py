"""Configuration management for the train queue system."""
import os
from typing import Optional
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Application configuration."""
    queue_timeout: int = Field(default=300, description="Default 5 minutes in seconds")
    allow_infinite_single_user: bool = Field(default=True)
    idle_timeout: int = Field(default=600, description="Default 10 minutes in seconds before auto-turning off lights")
    train_address: Optional[str] = Field(default=None, description="LionChief train BLE address")
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)


# Global configuration instance
config = AppConfig(
    queue_timeout=int(os.getenv("TRAIN_QUEUE_TIMEOUT", "300")),
    allow_infinite_single_user=os.getenv("TRAIN_ALLOW_INFINITE_SINGLE", "true").lower() == "true",
    idle_timeout=int(os.getenv("TRAIN_IDLE_TIMEOUT", "600")),
    train_address=os.getenv("TRAIN_ADDRESS"),
    server_host=os.getenv("TRAIN_SERVER_HOST", "0.0.0.0"),
    server_port=int(os.getenv("TRAIN_SERVER_PORT", "8000")),
)
