"""Logging utility module"""

import logging
from typing import Optional

_loggers: dict[str, logging.Logger] = {}


def get_logger_instance(name: str) -> logging.Logger:
    """
    Get or create a configured logger instance safely per module.
    Python's logging module inherently manages singletons based on the 'name' key.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Note:
        Log level defaults to INFO but can be updated after settings initialization.
        Loggers created before settings initialization will have their level updated
        when settings are finalized.
    """
    global _loggers

    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    if logger.hasHandlers():
        _loggers[name] = logger
        return logger

    # Default log level - will be updated by update_loggers_from_settings() if needed
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.propagate = False

    _loggers[name] = logger

    return logger


def update_loggers_from_settings() -> None:
    """
    Update all existing loggers with the LOG_LEVEL from settings.

    Call this after settings have been initialized from Spark properties.
    This ensures that the log level from Spark configuration takes effect.
    """
    from .settings import get_settings_instance

    settings = get_settings_instance()
    log_level = getattr(settings, "LOG_LEVEL", "INFO")

    for logger in _loggers.values():
        logger.setLevel(log_level)
