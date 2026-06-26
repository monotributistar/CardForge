"""Tests for config loader — reads and parses JSON config files."""

import json
import os
import pytest
from cardforge.config.loader import load_config, ConfigLoadError


class TestLoadConfig:
    """Test loading JSON configuration files."""

    def test_loads_valid_json(self, tmp_path):
        """Should parse a valid JSON file and return a dict."""
        config = {
            "project": {"name": "Test Card", "type": "business-card"},
            "object": {"width": 85, "height": 54, "thickness": 1.8},
        }
        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(config))

        result = load_config(str(config_file))

        assert result == config
        assert result["project"]["name"] == "Test Card"
        assert result["object"]["width"] == 85

    def test_file_not_found_raises(self, tmp_path):
        """Should raise ConfigLoadError when file doesn't exist."""
        missing = tmp_path / "does_not_exist.json"

        with pytest.raises(ConfigLoadError, match="Config file not found"):
            load_config(str(missing))

    def test_invalid_json_raises(self, tmp_path):
        """Should raise ConfigLoadError for malformed JSON."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{not valid json!!!")

        with pytest.raises(ConfigLoadError, match="Invalid JSON"):
            load_config(str(bad_file))

    def test_empty_file_raises(self, tmp_path):
        """Should raise ConfigLoadError for empty file."""
        empty = tmp_path / "empty.json"
        empty.write_text("")

        with pytest.raises(ConfigLoadError, match="Invalid JSON"):
            load_config(str(empty))

    def test_loads_real_example_config(self):
        """Should load the actual example config from the project."""
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_path = os.path.join(
            repo_root, "configs", "examples", "business_card_basic.json"
        )

        result = load_config(config_path)

        assert result["project"]["type"] == "business-card"
        assert result["object"]["width"] == 85.0
        assert len(result["faces"]["front"]["features"]) == 2
        assert len(result["faces"]["back"]["features"]) == 2

    def test_returns_dict(self, tmp_path):
        """Should always return a dict."""
        config = {"key": "value"}
        config_file = tmp_path / "simple.json"
        config_file.write_text(json.dumps(config))

        result = load_config(str(config_file))

        assert isinstance(result, dict)
