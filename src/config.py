"""Configuration module - loads and validates environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


class Config:
    """Application configuration loaded from environment variables."""

    # Telegram
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")

    # Gemini AI - supports multiple keys (comma-separated)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_API_KEYS: list[str] = [
        key.strip() for key in os.getenv("GEMINI_API_KEYS", "").split(",") if key.strip()
    ]

    @classmethod
    def get_all_gemini_keys(cls) -> list[str]:
        """Get all available Gemini API keys (from both GEMINI_API_KEY and GEMINI_API_KEYS)."""
        keys = []
        # Add single key if exists
        if cls.GEMINI_API_KEY:
            keys.append(cls.GEMINI_API_KEY)
        # Add multiple keys if exists
        for key in cls.GEMINI_API_KEYS:
            if key and key not in keys:  # Avoid duplicates
                keys.append(key)
        return keys

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(DATA_DIR / "bot.db"))

    # Timezone
    TIMEZONE: str = "Asia/Kuala_Lumpur"

    # Allowed user ID (only this user can use the bot)
    ALLOWED_USER_ID: int = int(os.getenv("ALLOWED_USER_ID", "561393547"))

    @classmethod
    def validate(cls) -> list[str]:
        """Validate required configuration. Returns list of missing keys."""
        missing = []

        if not cls.TELEGRAM_TOKEN:
            missing.append("TELEGRAM_TOKEN")

        if not cls.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")

        return missing

    @classmethod
    def is_valid(cls) -> bool:
        """Check if all required configuration is present."""
        return len(cls.validate()) == 0


# Convenience access
config = Config()
