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

    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(DATA_DIR / "bot.db"))

    # Timezone
    TIMEZONE: str = "Asia/Kuala_Lumpur"

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
