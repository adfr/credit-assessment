"""
Configuration Loader for Credit Risk Platform.

Loads the appropriate configuration based on APP_ENV environment variable.
Supports environment variable substitution in YAML config files.

Usage:
    from config import get_config, get_environment

    # Get current environment
    env = get_environment()  # "local" or "production"

    # Get config value
    config = get_config()
    db_url = config["database"]["url"]
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(Exception):
    """Raised when configuration loading fails."""

    pass


# Valid environments
VALID_ENVIRONMENTS = {"local", "production"}

# Default environment
DEFAULT_ENVIRONMENT = "local"

# Global config cache
_config_cache: dict[str, Any] | None = None
_current_environment: str | None = None


def get_config_dir() -> Path:
    """Get the config directory path."""
    project_root = Path(os.environ.get("PROJECT_ROOT", "/home/cdsw"))
    return project_root / "config"


def get_environment() -> str:
    """
    Get the current environment from APP_ENV.

    Returns:
        str: Current environment ("local" or "production")
    """
    global _current_environment

    if _current_environment is not None:
        return _current_environment

    env = os.environ.get("APP_ENV", DEFAULT_ENVIRONMENT).lower()

    if env not in VALID_ENVIRONMENTS:
        print(
            f"[WARN] Invalid APP_ENV='{env}'. "
            f"Valid options: {VALID_ENVIRONMENTS}. "
            f"Defaulting to '{DEFAULT_ENVIRONMENT}'."
        )
        env = DEFAULT_ENVIRONMENT

    _current_environment = env
    return env


def _substitute_env_vars(value: str) -> str:
    """
    Substitute environment variables in a string.

    Supports two formats:
    - ${VAR_NAME} - Required variable (raises error if not set)
    - ${VAR_NAME:-default} - Optional variable with default

    Args:
        value: String potentially containing env var references

    Returns:
        String with env vars substituted
    """
    if not isinstance(value, str):
        return value

    # Pattern for ${VAR:-default} or ${VAR}
    pattern = r"\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}"

    def replace_match(match):
        var_name = match.group(1)
        default_value = match.group(2)

        env_value = os.environ.get(var_name)

        if env_value is not None:
            return env_value
        elif default_value is not None:
            return default_value
        else:
            # Return empty string for unset optional vars
            return ""

    return re.sub(pattern, replace_match, value)


def _process_config_values(obj: Any) -> Any:
    """
    Recursively process config values, substituting env vars.

    Args:
        obj: Config object (dict, list, or scalar)

    Returns:
        Processed config object
    """
    if isinstance(obj, dict):
        return {key: _process_config_values(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_process_config_values(item) for item in obj]
    elif isinstance(obj, str):
        return _substitute_env_vars(obj)
    else:
        return obj


def load_config(environment: str | None = None, force_reload: bool = False) -> dict[str, Any]:
    """
    Load configuration for the specified environment.

    Args:
        environment: Environment to load ("local" or "production").
                    If None, uses APP_ENV environment variable.
        force_reload: If True, reload config even if cached.

    Returns:
        dict: Configuration dictionary

    Raises:
        ConfigurationError: If config file not found or invalid
    """
    global _config_cache, _current_environment

    if environment is None:
        environment = get_environment()

    # Return cached config if available
    if not force_reload and _config_cache is not None and _current_environment == environment:
        return _config_cache

    # Validate environment
    if environment not in VALID_ENVIRONMENTS:
        raise ConfigurationError(
            f"Invalid environment: '{environment}'. "
            f"Valid options: {VALID_ENVIRONMENTS}"
        )

    # Load config file
    config_dir = get_config_dir()
    config_file = config_dir / f"{environment}.yaml"

    if not config_file.exists():
        raise ConfigurationError(
            f"Configuration file not found: {config_file}"
        )

    try:
        with open(config_file, "r") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in {config_file}: {e}")

    # Process environment variable substitutions
    config = _process_config_values(raw_config)

    # Cache the config
    _config_cache = config
    _current_environment = environment

    return config


def get_config() -> dict[str, Any]:
    """
    Get the current configuration.

    Loads config if not already cached.

    Returns:
        dict: Configuration dictionary
    """
    if _config_cache is None:
        load_config()
    return _config_cache


def get_nested(config: dict, *keys: str, default: Any = None) -> Any:
    """
    Safely get a nested config value.

    Args:
        config: Configuration dictionary
        *keys: Keys to traverse (e.g., "database", "url")
        default: Default value if key not found

    Returns:
        Config value or default

    Example:
        db_url = get_nested(config, "database", "url", default="sqlite:///./data.db")
    """
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == "production"


def is_local() -> bool:
    """Check if running in local environment."""
    return get_environment() == "local"


def reset_config():
    """Reset the configuration cache. Useful for testing."""
    global _config_cache, _current_environment
    _config_cache = None
    _current_environment = None


# Auto-load on import for convenience
if os.environ.get("SKIP_CONFIG_AUTOLOAD") != "1":
    try:
        load_config()
    except ConfigurationError:
        # Don't fail on import, let it fail when config is accessed
        pass
