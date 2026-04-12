"""Logging utility module"""

import logging
import os
from logging.handlers import RotatingFileHandler
from .settings import get_settings_instance

settings_instance = get_settings_instance()


def get_logger(name: str) -> logging.Logger:
    """
    Create and configure a logger instance

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        return logger  # Return existing logger if already configured

    logger.setLevel(settings_instance.LOG_LEVEL)

    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(settings_instance.LOG_FILE), exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        settings_instance.LOG_FILE,
        maxBytes=settings_instance.LOG_MAX_BYTES,
        backupCount=settings_instance.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Prevent duplicate handlers
    logger.propagate = False

    return logger


_logger_instance: logging.Logger = None


def get_logger_instance(name: str) -> logging.Logger:
    """
    Get a singleton logger instance

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = get_logger(name)
    return _logger_instance
