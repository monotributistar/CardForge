"""Tests for config validator — schema + range + consistency checks."""

import pytest
from cardforge.config.validator import validate_config, ValidationError


class TestValidateConfig:
    """Test config validation against schema and rules."""

    # ── Valid config ──────────────────────────────────────────────

    def test_valid_minimal_config_passes(self):
        """A minimal valid config should pass validation."""
        config = {
            "project": {"name": "Test", "type": "business-card", "version": "0.1.0"},
            "manufacturing": {"process": "fdm", "nozzle": 0.4, "layerHeight": 0.2, "units": "mm"},
            "object": {"width": 85, "height": 54, "thickness": 1.8, "cornerRadius": 4},
            "owner": {"name": "Test"},
            "faces": {
                "front": {"features": []},
                "back": {"features": []},
            },
            "exports": {},
        }
        result = validate_config(config)
        assert result == config

    # ── Missing required keys ─────────────────────────────────────

    def test_missing_object_raises(self):
        """Should raise ValidationError when 'object' is missing."""
        config = {
            "project": {"name": "Test", "type": "business-card", "version": "0.1.0"},
            "manufacturing": {"process": "fdm", "nozzle": 0.4, "layerHeight": 0.2, "units": "mm"},
            "owner": {"name": "Test"},
            "faces": {"front": {"features": []}, "back": {"features": []}},
        }
        with pytest.raises(ValidationError, match="'object'"):
            validate_config(config)

    # ── Type validation ───────────────────────────────────────────

    def test_width_not_number_raises(self):
        """Should raise when object.width is not a number."""
        config = self._minimal_config()
        config["object"]["width"] = "85"
        with pytest.raises(ValidationError, match="not of type"):
            validate_config(config)

    # ── Range validation ──────────────────────────────────────────

    def test_zero_thickness_raises(self):
        """Should raise when thickness is 0 or negative."""
        config = self._minimal_config()
        config["object"]["thickness"] = 0
        with pytest.raises(ValidationError, match="thickness"):
            validate_config(config)

    def test_negative_thickness_raises(self):
        config = self._minimal_config()
        config["object"]["thickness"] = -1
        with pytest.raises(ValidationError, match="thickness"):
            validate_config(config)

    def test_thickness_too_large_raises(self):
        """Should raise when thickness > 3.0 mm."""
        config = self._minimal_config()
        config["object"]["thickness"] = 5.0
        with pytest.raises(ValidationError, match="thickness"):
            validate_config(config)

    def test_corner_radius_exceeds_half_width_raises(self):
        """Should raise when cornerRadius > min(width,height)/2."""
        config = self._minimal_config()
        config["object"]["cornerRadius"] = 50  # half of 100
        with pytest.raises(ValidationError, match="cornerRadius"):
            validate_config(config)

    # ── Relief validation ─────────────────────────────────────────

    def test_emboss_height_exceeds_half_thickness_raises(self):
        """Emboss height must not exceed half the object thickness."""
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "t1",
                "type": "text-block",
                "fontSize": 3.0,
                "lines": ["Hello"],
                "relief": {"mode": "emboss", "height": 5.0},
            }
        ]
        with pytest.raises(ValidationError, match="Emboss height"):
            validate_config(config)

    def test_deboss_depth_exceeds_half_thickness_raises(self):
        """Deboss depth must not exceed half the object thickness."""
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "p1",
                "type": "pattern",
                "patternType": "text-repeat",
                "text": "X",
                "relief": {"mode": "deboss", "depth": 5.0},
            }
        ]
        with pytest.raises(ValidationError, match="Deboss depth"):
            validate_config(config)

    def test_cut_depth_exceeds_thickness_raises(self):
        """Cut depth must not exceed object thickness."""
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "c1",
                "type": "frame",
                "relief": {"mode": "cut", "depth": 5.0},
            }
        ]
        with pytest.raises(ValidationError, match="Cut depth"):
            validate_config(config)

    # ── QR validation ─────────────────────────────────────────────

    def test_qr_size_too_small_raises(self):
        """QR code must be at least 22 mm."""
        config = self._minimal_config()
        config["qr"] = {
            "enabled": True,
            "type": "vcard",
            "target": "owner",
            "size": 10,
        }
        config["faces"]["back"]["features"] = [
            {"id": "qr1", "type": "qr", "source": "qr"}
        ]
        with pytest.raises(ValidationError, match="QR"):
            validate_config(config)

    # ── Template variable checking ────────────────────────────────

    def test_unresolved_variable_raises(self):
        """Should detect template variables that can't resolve."""
        config = self._minimal_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "t1",
                "type": "text-block",
                "fontSize": 3.0,
                "lines": ["Hello {{owner.nonexistent}}"],
            }
        ]
        with pytest.raises(ValidationError, match="Unresolved"):
            validate_config(config)

    def test_valid_template_variable_passes(self):
        """Should allow template variables that resolve to existing paths."""
        config = self._minimal_config()
        config["owner"] = {"name": "Javier", "title": "Dev"}
        config["faces"]["front"]["features"] = [
            {
                "id": "t1",
                "type": "text-block",
                "fontSize": 3.0,
                "lines": ["{{owner.name}}", "{{owner.title}}"],
            }
        ]
        result = validate_config(config)
        assert result == config

    # ── helper ────────────────────────────────────────────────────

    @staticmethod
    def _minimal_config():
        return {
            "project": {"name": "Test", "type": "business-card", "version": "0.1.0"},
            "manufacturing": {"process": "fdm", "nozzle": 0.4, "layerHeight": 0.2, "units": "mm"},
            "object": {"width": 85, "height": 54, "thickness": 1.8, "cornerRadius": 4},
            "owner": {"name": "Test Owner"},
            "faces": {
                "front": {"features": []},
                "back": {"features": []},
            },
            "exports": {},
        }
