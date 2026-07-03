"""Tests for v2 variable resolution."""

import pytest

from cardforge.document.variables import UnresolvedVariableError, resolve_variables


def doc_with(faces, variables=None, assets=None):
    return {
        "cardforge": "2.0",
        "variables": variables or {},
        "assets": assets or {},
        "faces": faces,
    }


class TestResolveVariables:
    def test_simple_substitution(self):
        doc = doc_with(
            {"front": {"features": [{"lines": ["Hola {{name}}"]}]}},
            variables={"name": "Ada"})
        out = resolve_variables(doc)
        assert out["faces"]["front"]["features"][0]["lines"] == ["Hola Ada"]

    def test_multiple_vars_in_one_string(self):
        doc = doc_with(
            {"front": {"features": [{"text": "{{name}} <{{email}}>"}]}},
            variables={"name": "Ada", "email": "ada@x.dev"})
        out = resolve_variables(doc)
        assert out["faces"]["front"]["features"][0]["text"] == "Ada <ada@x.dev>"

    def test_asset_reference(self):
        doc = doc_with(
            {"front": {"features": [{"svgAsset": "{{assets.logo}}"}]}},
            assets={"logo": "assets/logo.svg"})
        out = resolve_variables(doc)
        assert out["faces"]["front"]["features"][0]["svgAsset"] == "assets/logo.svg"

    def test_nested_fields_resolved(self):
        doc = doc_with(
            {"back": {"features": [{"fields": {"url": "{{website}}"}}]}},
            variables={"website": "https://ada.dev"})
        out = resolve_variables(doc)
        assert out["faces"]["back"]["features"][0]["fields"]["url"] == "https://ada.dev"

    def test_unresolved_raises_with_location(self):
        doc = doc_with({"front": {"features": [{"lines": ["{{missing}}"]}]}})
        with pytest.raises(UnresolvedVariableError, match="missing"):
            resolve_variables(doc)

    def test_original_not_mutated(self):
        doc = doc_with(
            {"front": {"features": [{"lines": ["{{name}}"]}]}},
            variables={"name": "Ada"})
        resolve_variables(doc)
        assert doc["faces"]["front"]["features"][0]["lines"] == ["{{name}}"]

    def test_variables_section_stays_verbatim(self):
        doc = doc_with(
            {"front": {"features": []}},
            variables={"sig": "{{name}}", "name": "Ada"})
        out = resolve_variables(doc)
        assert out["variables"]["sig"] == "{{name}}"
