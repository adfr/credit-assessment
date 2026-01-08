"""
Configuration module for Credit Risk Platform.
Supports local development and production (Cloudera) modes.
"""

from .config_loader import (
    load_config,
    get_config,
    get_environment,
    get_nested,
    is_production,
    is_local,
    reset_config,
    ConfigurationError,
)

__all__ = [
    "load_config",
    "get_config",
    "get_environment",
    "get_nested",
    "is_production",
    "is_local",
    "reset_config",
    "ConfigurationError",
]
