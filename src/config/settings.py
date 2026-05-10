"""Configuration settings for the Football Scout Pro application."""
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional


class DatabaseConfig(BaseModel):
    """Database configuration."""
    player_stats_path: Path = Field(default=Path("data/playerstats.csv"))
    players_info_path: Path = Field(default=Path("data/players_info.csv"))
    watchlist_path: Path = Field(default=Path("data/watchlist.json"))


class AppConfig(BaseModel):
    """Application configuration."""
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    app_title: str = "Football Scout Pro"
    app_subtitle: str = "Professional Player Analytics & Scouting Tool"
    log_level: str = "INFO"
    
    class Config:
        arbitrary_types_allowed = True


def get_config() -> AppConfig:
    """Get application configuration."""
    return AppConfig()
