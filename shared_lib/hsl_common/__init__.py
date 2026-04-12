"""Common services for HSL Bus system"""

from .settings import get_settings_instance
from .logger import get_logger_instance

__all__ = [
    "get_settings_instance",
    "get_logger_instance",
]
