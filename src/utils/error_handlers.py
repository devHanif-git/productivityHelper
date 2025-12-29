"""Error handling utilities for the bot."""

import logging
from functools import wraps
from typing import Callable, Any

from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TelegramError, NetworkError, TimedOut

logger = logging.getLogger(__name__)


# Default error messages
ERROR_MESSAGES = {
    "general": "Sorry, something went wrong. Please try again.",
    "network": "Network error. Please check your connection and try again.",
    "timeout": "Request timed out. Please try again.",
    "api": "Failed to process your request. Please try again later.",
    "image_parse": "I couldn't read that image. Please try with a clearer photo.",
    "not_found": "The requested item was not found.",
    "database": "Database error. Please try again.",
}


class BotError(Exception):
    """Base exception for bot errors."""

    def __init__(self, message: str, user_message: str = None):
        super().__init__(message)
        self.user_message = user_message or ERROR_MESSAGES["general"]


class ImageParseError(BotError):
    """Error parsing image with AI."""

    def __init__(self, message: str = "Failed to parse image"):
        super().__init__(message, ERROR_MESSAGES["image_parse"])


class DatabaseError(BotError):
    """Database operation error."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, ERROR_MESSAGES["database"])


class APIError(BotError):
    """External API error."""

    def __init__(self, message: str = "API request failed"):
        super().__init__(message, ERROR_MESSAGES["api"])


def handler_error_wrapper(func: Callable) -> Callable:
    """
    Decorator to wrap handler functions with error handling.

    Usage:
        @handler_error_wrapper
        async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            ...
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except BotError as e:
            logger.error(f"Bot error in {func.__name__}: {e}")
            if update and update.message:
                await update.message.reply_text(e.user_message)
        except TimedOut as e:
            logger.error(f"Timeout in {func.__name__}: {e}")
            if update and update.message:
                await update.message.reply_text(ERROR_MESSAGES["timeout"])
        except NetworkError as e:
            logger.error(f"Network error in {func.__name__}: {e}")
            if update and update.message:
                await update.message.reply_text(ERROR_MESSAGES["network"])
        except TelegramError as e:
            logger.error(f"Telegram error in {func.__name__}: {e}")
            if update and update.message:
                await update.message.reply_text(ERROR_MESSAGES["general"])
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            if update and update.message:
                await update.message.reply_text(ERROR_MESSAGES["general"])

    return wrapper


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Global error handler for the application.

    Register with: application.add_error_handler(error_handler)
    """
    logger.error(f"Exception while handling an update: {context.error}")

    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(ERROR_MESSAGES["general"])
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


def safe_execute(default: Any = None):
    """
    Decorator for functions that should return a default value on error.

    Usage:
        @safe_execute(default=[])
        def get_items():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return default
        return wrapper
    return decorator


async def safe_execute_async(default: Any = None):
    """
    Async decorator for functions that should return a default value on error.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return default
        return wrapper
    return decorator
