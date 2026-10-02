"""GET /api/schema — format discovery for clients and agents."""

from fastapi.testclient import TestClient

from cardforge.api.server import app
from cardforge.document.schema_v2 import load_schema

client = TestClient(app)

FEATURE_TYPES = {"text-block", "text-pattern", "pattern", "qr",
                 "icon", "shape", "hole", "pocket"}


class TestSchemaFull:
    def test_returns_the_whole_schema(self):
        r = client.get("/api/schema")
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["section"] == "full"
        assert body["schema"] == load_schema()

    def test_schema_is_self_describing(self):
        """A client must be able to validate against what it receives."""
        schema = client.get("/api/schema").json()["schema"]
        assert "$defs" in schema
        assert set(schema["required"]) >= {"cardforge", "meta", "object",
                                           "materials", "faces"}


class TestSchemaFeatures:
    def test_lists_every_feature_type(self):
        r = client.get("/api/schema", params={"section": "features"})
        assert r.status_code == 200
        body = r.json()
        assert set(body["types"]) == FEATURE_TYPES

    def test_includes_the_shared_base(self):
        """The per-type branches only carry their own fields; without the base
        a caller would not know id/transform/material/relief are mandatory."""
        body = client.get("/api/schema",
                          params={"section": "features"}).json()
        assert set(body["base"]["required"]) == {"id", "type", "transform",
                                                 "material", "relief"}

    def test_branch_carries_its_own_requirements(self):
        body = client.get("/api/schema",
                          params={"section": "features"}).json()
        text = body["types"]["text-block"]
        assert set(text["required"]) >= {"lines", "font"}


class TestSchemaErrors:
    def test_unknown_section_is_rejected(self):
        r = client.get("/api/schema", params={"section": "nope"})
        assert r.status_code == 400
        assert r.json()["ok"] is False
