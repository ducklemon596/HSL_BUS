"""Logging utility module"""

import logging
from .settings import get_settings_instance

settings_instance = get_settings_instance()


def get_logger_instance(name: str) -> logging.Logger:
    """
    Get or create a configured logger instance safely per module.
    Python's logging module inherently manages singletons based on the 'name' key.

    Args:
        name: Logger name (typically __name__)
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    logger.setLevel(settings_instance.LOG_LEVEL)

    formatter = logging.Formatter(
        "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.propagate = False

    return logger
