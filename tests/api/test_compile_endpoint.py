"""API v2 endpoint tests via FastAPI TestClient."""

import base64
import json
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from cardforge.api.server import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
client = TestClient(app)


def example_doc():
    return json.loads(
        (PROJECT_ROOT / "examples" / "javier.cardforge.json").read_text())


class TestHealth:
    def test_health(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["ok"] is True


class TestCompile:
    def test_compile_v1_document(self):
        r = client.post("/api/compile", json={"document": example_doc()})
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        # the base64 payload must be a valid 3MF zip
        data = base64.b64decode(body["model3mfBase64"])
        with zipfile.ZipFile(BytesIO(data)) as zf:
            assert "3D/3dmodel.model" in zf.namelist()
        assert body["stats"]["featureCount"] > 0
        mats = {m["id"]: m for m in body["materials"]}
        assert mats["base"]["present"] is True
        assert mats["base"]["color"] == "#1a1a1a"
        assert isinstance(body["constraints"], list)
        assert body["manufacturing"]["score"] >= 0

    def test_invalid_document_400(self):
        r = client.post("/api/compile", json={"document": {"nope": 1}})
        assert r.status_code == 400

    def test_schema_violation_422(self):
        doc = {
            "cardforge": "2.0",
            "meta": {"id": "x", "name": "X"},
            "object": {"outline": {"type": "rect", "width": 10, "height": 10},
                       "thickness": 1.0},
            "materials": [],  # violates minItems
            "faces": {},
        }
        r = client.post("/api/compile", json={"document": doc})
        assert r.status_code == 422
        assert r.json()["details"]


class TestExport:
    def test_export_zip(self):
        r = client.post("/api/export", json={
            "document": example_doc(), "ignoreErrors": True})
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        with zipfile.ZipFile(BytesIO(r.content)) as zf:
            names = zf.namelist()
            assert any(n.endswith(".3mf") for n in names)
            assert any(n.startswith("stl/") for n in names)
            assert "manufacturing_report.json" in names


class TestMigrate:
    def test_migrate_v1(self):
        r = client.post("/api/migrate", json={"document": example_doc()})
        assert r.status_code == 200
        body = r.json()
        assert body["migrated"] is True
        assert body["document"]["cardforge"] == "2.0"

    def test_v2_passthrough(self):
        v2 = client.post("/api/migrate", json={"document": example_doc()}).json()["document"]
        r = client.post("/api/migrate", json={"document": v2})
        assert r.json()["migrated"] is False
