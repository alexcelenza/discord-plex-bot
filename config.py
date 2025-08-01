"""
Configuration settings for the Discord Plex Bot
"""
import os
from typing import Optional

class Config:
    # Discord Settings
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    GUILD_ID: int = int(os.getenv("GUILD_ID", "0"))
    USER_ID: int = int(os.getenv("USER_ID", "0"))
    
    # Plex Settings
    PLEX_URL: str = os.getenv("PLEX_URL", "")
    PLEX_TOKEN: str = os.getenv("PLEX_TOKEN", "")
    PLEX_LIBRARY_NAME: str = os.getenv("PLEX_LIBRARY_NAME", "Library of Congress")
    
    # Rate Limiting
    RATE_LIMIT_WINDOW: int = 60  # seconds
    RATE_LIMIT_MAX_REQUESTS: int = 5  # max requests per window
    
    # Search Settings
    MAX_SEARCH_RESULTS: int = 10
    MIN_SIMILARITY_THRESHOLD: float = 0.5  # Increased from 0.3 to be more strict
    MAX_MOVIE_TITLE_LENGTH: int = 100
    MIN_MOVIE_TITLE_LENGTH: int = 2
    
    # UI Settings
    MAX_EMBEDS_PER_MESSAGE: int = 10
    MAX_BUTTONS_PER_VIEW: int = 5
    BUTTON_TIMEOUT: int = 60  # seconds
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """Validate that all required environment variables are set"""
        required_vars = [
            cls.DISCORD_TOKEN,
            cls.GUILD_ID,
            cls.USER_ID,
            cls.PLEX_URL,
            cls.PLEX_TOKEN
        ]
        return all(required_vars)
    
    @classmethod
    def get_missing_vars(cls) -> list[str]:
        """Get list of missing environment variables"""
        missing = []
        if not cls.DISCORD_TOKEN:
            missing.append("DISCORD_TOKEN")
        if not cls.GUILD_ID:
            missing.append("GUILD_ID")
        if not cls.USER_ID:
            missing.append("USER_ID")
        if not cls.PLEX_URL:
            missing.append("PLEX_URL")
        if not cls.PLEX_TOKEN:
            missing.append("PLEX_TOKEN")
        return missing 