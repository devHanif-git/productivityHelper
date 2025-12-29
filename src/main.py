"""Main entry point for the UTeM Student Assistant Bot."""

import asyncio
import logging
import sys

from telegram.ext import Application

from .config import config, Config
from .database.models import init_db
from .bot.handlers import register_handlers
from .scheduler.notifications import start_scheduler, stop_scheduler
from .utils.logging_config import setup_logging
from .utils.error_handlers import error_handler

# Configure logging with file output
setup_logging(log_level=logging.INFO, log_to_file=True)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Called after the application is initialized."""
    # Start the notification scheduler
    logger.info("Starting notification scheduler...")
    start_scheduler(application.bot)


async def post_shutdown(application: Application) -> None:
    """Called when the application is shutting down."""
    # Stop the notification scheduler
    logger.info("Stopping notification scheduler...")
    stop_scheduler()


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
    application = (
        Application.builder()
        .token(config.TELEGRAM_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register handlers
    register_handlers(application)

    # Register global error handler
    application.add_error_handler(error_handler)

    # Run the bot until Ctrl+C
    logger.info("Bot is running. Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()
