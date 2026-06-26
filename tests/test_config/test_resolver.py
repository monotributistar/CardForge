"""Tests for config variable resolver — {{var}} template substitution."""

import pytest
from cardforge.config.resolver import resolve_config, UnresolvedVariableError


class TestResolveConfig:
    """Test template variable resolution in config."""

    def test_resolves_simple_variable(self):
        """{{owner.name}} should resolve to the actual value."""
        config = {
            "project": {"name": "Test", "type": "business-card", "version": "0.1.0"},
            "manufacturing": {"process": "fdm", "nozzle": 0.4, "layerHeight": 0.2, "units": "mm"},
            "object": {"width": 85, "height": 54, "thickness": 1.8, "cornerRadius": 4},
            "owner": {"name": "Javier", "title": "Developer"},
            "faces": {
                "front": {
                    "features": [
                        {
                            "id": "t1",
                            "type": "text-block",
                            "fontSize": 3.0,
                            "lines": ["Hello {{owner.name}}"],
                        }
                    ]
                },
                "back": {"features": []},
            },
        }
        result = resolve_config(config)
        assert result["faces"]["front"]["features"][0]["lines"][0] == "Hello Javier"

    def test_resolves_multiple_variables_in_line(self):
        """Multiple {{var}} references in one line should all resolve."""
        config = self._base_config()
        config["owner"] = {"name": "Javier", "title": "Dev"}
        config["faces"]["front"]["features"] = [
            {
                "id": "t1",
                "type": "text-block",
                "fontSize": 3.0,
                "lines": ["{{owner.name}} - {{owner.title}}"],
            }
        ]
        result = resolve_config(config)
        assert result["faces"]["front"]["features"][0]["lines"][0] == "Javier - Dev"

    def test_resolves_nested_variable(self):
        """{{owner.contact.email}} should resolve through nested dict."""
        config = self._base_config()
        config["owner"] = {"contact": {"email": "javier@test.com"}}
        config["faces"]["front"]["features"] = [
            {
                "id": "t1",
                "type": "text-block",
                "fontSize": 3.0,
                "lines": ["Email: {{owner.contact.email}}"],
            }
        ]
        result = resolve_config(config)
        assert result["faces"]["front"]["features"][0]["lines"][0] == "Email: javier@test.com"

    def test_no_variables_returns_unchanged(self):
        """Config with no template variables should be structurally identical."""
        config = self._base_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "t1",
                "type": "text-block",
                "fontSize": 3.0,
                "lines": ["Plain text, no variables"],
            }
        ]
        result = resolve_config(config)
        assert result["faces"]["front"]["features"][0]["lines"][0] == "Plain text, no variables"

    def test_unresolved_variable_raises(self):
        """Unresolved template vars should raise UnresolvedVariableError."""
        config = self._base_config()
        config["faces"]["front"]["features"] = [
            {
                "id": "t1",
                "type": "text-block",
                "fontSize": 3.0,
                "lines": ["{{owner.missing_field}}"],
            }
        ]
        with pytest.raises(UnresolvedVariableError, match="missing_field"):
            resolve_config(config)

    def test_does_not_mutate_original(self):
        """Resolver should return a new dict, not modify the original."""
        config = self._base_config()
        config["owner"] = {"name": "Original"}
        config["faces"]["front"]["features"] = [
            {
                "id": "t1",
                "type": "text-block",
                "fontSize": 3.0,
                "lines": ["{{owner.name}}"],
            }
        ]
        original_lines = config["faces"]["front"]["features"][0]["lines"][:]

        result = resolve_config(config)

        # Result should have resolved value
        assert result["faces"]["front"]["features"][0]["lines"][0] == "Original"
        # Original should still have the template
        assert config["faces"]["front"]["features"][0]["lines"] == original_lines

    def test_resolves_qr_target(self):
        """QR source references should be resolved."""
        config = self._base_config()
        config["owner"] = {"name": "Javier", "email": "j@test.com"}
        config["qr"] = {
            "enabled": True,
            "type": "vcard",
            "target": "owner",
            "size": 24,
        }
        # The qr.source="qr" means "use the top-level qr config"
        # Resolver doesn't need to change qr config itself — it just resolves vars
        result = resolve_config(config)
        assert result["qr"]["target"] == "owner"

    # ── helper ────────────────────────────────────────────────────

    @staticmethod
    def _base_config():
        return {
            "project": {"name": "Test", "type": "business-card", "version": "0.1.0"},
            "manufacturing": {"process": "fdm", "nozzle": 0.4, "layerHeight": 0.2, "units": "mm"},
            "object": {"width": 85, "height": 54, "thickness": 1.8, "cornerRadius": 4},
            "owner": {"name": "Test Owner"},
            "faces": {
                "front": {"features": []},
                "back": {"features": []},
            },
        }
