"""Run script for the UTeM Student Assistant Bot."""

import logging
import sys

from telegram.ext import Application

from src.config import config, Config
from src.database.models import init_db
from src.bot.handlers import register_handlers

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Initialize and run the bot."""
    # Validate configuration
    missing = Config.validate()
    if missing:
        logger.error(f"Missing required configuration: {', '.join(missing)}")
        logger.error("Please check your .env file")
        sys.exit(1)

    # Initialize database
    logger.info(f"Initializing database at {config.DATABASE_PATH}")
    init_db(config.DATABASE_PATH)

    # Create the Application
    logger.info("Starting bot...")
    application = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Register handlers
    register_handlers(application)

    # Run the bot until Ctrl+C
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()
