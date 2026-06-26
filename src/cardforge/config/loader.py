"""Config loader — reads and parses JSON configuration files."""

import json
import os
from typing import Any, Dict


class ConfigLoadError(Exception):
    """Raised when a config file cannot be loaded or parsed."""

    pass


def load_config(path: str) -> Dict[str, Any]:
    """Load and parse a JSON configuration file.

    Args:
        path: Absolute or relative path to the JSON config file.

    Returns:
        Parsed config as a dictionary.

    Raises:
        ConfigLoadError: If the file doesn't exist or contains invalid JSON.
    """
    if not os.path.isfile(path):
        raise ConfigLoadError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigLoadError(f"Invalid JSON in config file: {e}") from e
