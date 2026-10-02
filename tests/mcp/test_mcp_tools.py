"""MCP tool surface — what an AI agent actually sees and gets back.

These go through `server.call_tool` rather than the plain functions, so the
schema generation and result serialisation are covered too.
"""

import asyncio
import json
from pathlib import Path

from cardforge.mcp_server import server

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MINIMAL = "examples/prototypes/card_minimal.cardforge.json"

FEATURE_TYPES = {"text-block", "text-pattern", "pattern", "qr",
                 "icon", "shape", "hole", "pocket"}


def call(name, **args):
    """Invoke a tool the way a client does; return its structured result."""
    result = asyncio.run(server.call_tool(name, args))
    return result.structured_content["result"]


def doc(**overrides):
    """A minimal valid v2 document, printable as-is."""
    d = {
        "cardforge": "2.0",
        "meta": {"id": "test-card", "name": "Test Card"},
        "object": {"outline": {"type": "rect", "width": 85, "height": 54},
                   "thickness": 1.8},
        "materials": [
            {"id": "base", "name": "Base", "color": "#111111",
             "role": "base", "slot": 1},
            {"id": "text", "name": "Text", "color": "#ffffff",
             "role": "text", "slot": 2},
        ],
        "faces": {"front": {"features": [
            {"id": "title", "type": "text-block",
             "transform": {"x": 10, "y": 10}, "material": "text",
             "relief": {"mode": "emboss", "height": 0.4},
             "lines": ["HOLA"], "align": "left",
             "font": {"family": "Arial", "size": 6, "weight": 700}},
        ]}},
    }
    d.update(overrides)
    return d


class TestToolSurface:
    def test_every_tool_is_registered(self):
        tools = asyncio.run(server.list_tools())
        assert {t.name for t in tools} == {
            "cardforge_guide", "cardforge_schema", "cardforge_fonts",
            "cardforge_compile", "cardforge_export", "cardforge_migrate",
            "cardforge_examples"}

    def test_every_tool_is_described(self):
        """An undescribed tool is invisible to a model choosing between them."""
        for t in asyncio.run(server.list_tools()):
            assert t.description and len(t.description) > 40


class TestGuide:
    def test_covers_every_feature_type(self):
        """The guide is generated from the schema, so a new feature type can
        never silently go undocumented."""
        assert set(call("cardforge_guide")["feature_types"]) == FEATURE_TYPES

    def test_states_the_anchor_convention(self):
        g = call("cardforge_guide")
        assert "TOP-LEFT" in g["coordinates"]["anchor"]

    def test_skeleton_is_a_valid_starting_point(self):
        """The skeleton must survive validation once features are added, or
        it teaches a shape the compiler rejects."""
        from cardforge.document.schema_v2 import validate_v2

        skeleton = call("cardforge_guide")["document_skeleton"]
        skeleton["variables"] = {}
        validate_v2(skeleton)


class TestVerdict:
    """The stopping condition for a prompt-driven run.

    Each case here scored 100/100 "Excellent — ready to print" under the
    manufacturing report alone while producing a card nobody would accept.
    """

    def test_ready_on_a_clean_document(self):
        v = call("cardforge_compile", document=doc())["verdict"]
        assert v["ready"] is True
        assert v["blockers"] == []

    def test_back_face_emboss_is_a_blocker(self):
        """Emboss on the bed-facing face is refused and the feature vanishes —
        the card comes out blank on that side."""
        d = doc()
        d["faces"] = {"back": {"features": [
            {"id": "qr", "type": "qr", "transform": {"x": 30, "y": 14},
             "material": "text", "relief": {"mode": "emboss", "height": 0.4},
             "qrType": "url", "fields": {"url": "https://example.com"},
             "size": 26}]}}
        out = call("cardforge_compile", document=d)

        assert out["manufacturing"]["score"] == 100      # the old signal lies
        assert out["manufacturing"]["errorCount"] == 0
        assert out["verdict"]["ready"] is False          # the new one does not
        assert any(b["code"] == "back-emboss-not-flat"
                   for b in out["verdict"]["blockers"])

    def test_pocket_breaking_through_is_a_blocker(self):
        d = doc()
        d["object"]["thickness"] = 0.9
        d["faces"]["front"]["features"] = [
            {"id": "nfc", "type": "pocket", "transform": {"x": 30, "y": 14},
             "material": "base", "relief": {"mode": "deboss", "depth": 0.9},
             "pocketType": "circle", "insert": "rfid",
             "diameter": 25, "depth": 0.9}]
        out = call("cardforge_compile", document=d)

        assert out["manufacturing"]["score"] == 100
        assert out["verdict"]["ready"] is False
        assert any(b["code"] == "pocket-breaks-through"
                   for b in out["verdict"]["blockers"])

    def test_a_skipped_feature_blocks(self):
        """Asking for something and not getting it is a failure, even when
        every rule the analyzer knows is satisfied."""
        d = doc()
        d["assets"] = {"logo": "assets/logos/does-not-exist.svg"}
        d["faces"]["front"]["features"].append(
            {"id": "logo", "type": "icon", "transform": {"x": 50, "y": 10},
             "material": "text", "relief": {"mode": "emboss", "height": 0.4},
             "svgAsset": "logo", "width": 15})
        out = call("cardforge_compile", document=d)

        assert out["verdict"]["ready"] is False
        skipped = [b for b in out["verdict"]["blockers"]
                   if b["code"] == "feature-skipped"]
        assert skipped and skipped[0]["featureId"] == "logo"

    def test_blockers_name_their_channel(self):
        """Three subsystems report problems; the verdict says which spoke so a
        caller can tell a geometry refusal from a printability warning."""
        d = doc()
        d["faces"]["front"]["features"][0]["font"] = {
            "family": "Arial", "size": 1.8, "weight": 300}
        v = call("cardforge_compile", document=d)["verdict"]
        assert {b["source"] for b in v["blockers"]} <= {
            "constraint", "manufacturing", "compiler"}
        assert any(b["source"] == "manufacturing" for b in v["blockers"])

    def test_summary_is_readable_either_way(self):
        assert call("cardforge_compile", document=doc())["verdict"]["summary"].startswith("Ready")
        d = doc()
        d["object"]["thickness"] = 0.9
        d["faces"]["front"]["features"] = [
            {"id": "nfc", "type": "pocket", "transform": {"x": 30, "y": 14},
             "material": "base", "relief": {"mode": "deboss", "depth": 0.9},
             "pocketType": "circle", "insert": "rfid",
             "diameter": 25, "depth": 0.9}]
        assert "Not ready" in call("cardforge_compile", document=d)["verdict"]["summary"]

    def test_compiler_notes_are_warnings_not_blockers(self):
        """A note about something the compiler adjusted but survived should
        not stop the run."""
        v = call("cardforge_compile", path=MINIMAL)["verdict"]
        assert v["ready"] is True
        assert all(b["code"] != "compiler-note" for b in v["blockers"])


class TestGuideTeachesTheVerdict:
    def test_stopping_condition_points_at_the_verdict(self):
        """The guide previously told the agent to stop on errorCount, which is
        the signal that lies."""
        g = call("cardforge_guide")
        assert g["stopping_condition"]["use"] == "verdict.ready"
        assert "score" in g["stopping_condition"]["do_not_use"]

    def test_warns_about_the_back_face(self):
        assert any("bed" in p or "back face" in p
                   for p in call("cardforge_guide")["pitfalls"])


class TestExamples:
    def test_lists_the_shipped_documents(self):
        out = call("cardforge_examples")
        assert out["count"] >= 4
        assert all("path" in e for e in out["examples"])

    def test_reports_readiness_per_example(self):
        """A starting point that does not compile clean is worse than none —
        the caller has to know which is which."""
        for e in call("cardforge_examples")["examples"]:
            assert isinstance(e["ready"], bool)

    def test_paths_are_loadable(self):
        for e in call("cardforge_examples")["examples"]:
            assert call("cardforge_compile", path=e["path"])["ok"] is True

    def test_document_included_on_request(self):
        out = call("cardforge_examples", include_document=True)
        assert all(e["document"]["cardforge"] == "2.0"
                   for e in out["examples"] if e.get("ready") is not None
                   and "document" in e)


class TestSchema:
    def test_features_section(self):
        assert set(call("cardforge_schema", section="features")["types"]) == FEATURE_TYPES

    def test_full_section(self):
        assert "$defs" in call("cardforge_schema", section="full")["schema"]

    def test_unknown_section_reports_the_valid_ones(self):
        out = call("cardforge_schema", section="nope")
        assert "features" in out["error"] and "full" in out["error"]


class TestFonts:
    def test_lists_families(self):
        assert call("cardforge_fonts")["total"] > 5

    def test_filter_narrows_the_list(self):
        everything = call("cardforge_fonts")["total"]
        filtered = call("cardforge_fonts", contains="arial")
        assert 0 < filtered["total"] < everything
        assert all("arial" in f["family"].lower() for f in filtered["fonts"])

    def test_limit_caps_the_payload(self):
        out = call("cardforge_fonts", limit=3)
        assert len(out["fonts"]) == 3
        assert out["total"] > 3  # total still reports the real count


class TestCompile:
    def test_compiles_an_inline_document(self):
        out = call("cardforge_compile", document=doc())
        assert out["ok"] is True
        assert out["manufacturing"]["errorCount"] == 0
        assert out["stats"]["featureCount"] == 1

    def test_compiles_a_v1_file_by_path(self):
        out = call("cardforge_compile", path=MINIMAL)
        assert out["ok"] is True
        assert out["stats"]["featureCount"] == 4

    def test_never_returns_geometry(self):
        """Geometry in a tool result would burn the agent's context for
        nothing — it cannot read a mesh."""
        out = call("cardforge_compile", document=doc())
        assert "model3mfBase64" not in out
        assert len(json.dumps(out)) < 20_000

    def test_feature_bounds_are_document_space(self):
        """A shape anchored at (10,10) sized 20x8 occupies exactly that box —
        this is the contract the guide teaches."""
        d = doc()
        d["faces"]["front"]["features"] = [
            {"id": "box", "type": "shape", "transform": {"x": 10, "y": 10},
             "material": "text", "relief": {"mode": "emboss", "height": 0.4},
             "shapeType": "rect", "width": 20, "height": 8}]
        b = call("cardforge_compile", document=d)["featureBounds"][0]
        assert (b["x"], b["y"], b["width"], b["height"]) == (10.0, 10.0, 20.0, 8.0)

    def test_saves_3mf_when_asked(self, tmp_path):
        target = tmp_path / "out.3mf"
        out = call("cardforge_compile", document=doc(), save_3mf_to=str(target))
        assert out["saved3mf"]["bytes"] == target.stat().st_size
        assert target.read_bytes()[:2] == b"PK"  # 3MF is a zip

    def test_thin_text_is_reported_with_a_fix(self):
        """The suggestion is what makes the loop closeable by an agent."""
        d = doc()
        d["faces"]["front"]["features"][0]["font"] = {
            "family": "Arial", "size": 1.8, "weight": 300}
        out = call("cardforge_compile", document=d)
        issues = out["manufacturing"]["issues"]
        assert out["manufacturing"]["errorCount"] > 0
        assert any(i["suggestion"] for i in issues)

    def test_unknown_material_fails_validation_with_the_offender_named(self):
        d = doc()
        d["faces"]["front"]["features"][0]["material"] = "ghost"
        out = call("cardforge_compile", document=d)
        assert out["ok"] is False
        assert out["stage"] == "validation"
        assert any("ghost" in p for p in out["problems"])

    def test_requires_exactly_one_input(self):
        assert call("cardforge_compile")["stage"] == "input"
        assert call("cardforge_compile", document=doc(),
                    path=MINIMAL)["stage"] == "input"

    def test_missing_file_is_reported_not_raised(self):
        out = call("cardforge_compile", path="nope/missing.json")
        assert out["ok"] is False and out["stage"] == "input"


class TestExport:
    def test_writes_the_package(self, tmp_path):
        out = call("cardforge_export", document=doc(), out_dir=str(tmp_path))
        assert out["ok"] is True
        names = {Path(f["path"]).name for f in out["files"]}
        assert "test-card.3mf" in names
        assert "manufacturing_report.json" in names
        assert any(n.endswith(".stl") for n in names)
        for f in out["files"]:
            assert Path(f["path"]).stat().st_size == f["bytes"]

    def test_formats_are_honoured(self, tmp_path):
        out = call("cardforge_export", document=doc(), out_dir=str(tmp_path),
                   formats=["3mf"])
        assert not any(f["path"].endswith(".stl") for f in out["files"])

    def test_blocking_errors_stop_the_export(self, tmp_path):
        d = doc()
        d["faces"]["front"]["features"][0]["font"] = {
            "family": "Arial", "size": 1.8, "weight": 300}
        out = call("cardforge_export", document=d, out_dir=str(tmp_path))
        assert out["ok"] is False and out["stage"] == "blocked"
        assert not list(tmp_path.iterdir())  # nothing written

    def test_ignore_errors_overrides(self, tmp_path):
        d = doc()
        d["faces"]["front"]["features"][0]["font"] = {
            "family": "Arial", "size": 1.8, "weight": 300}
        out = call("cardforge_export", document=d, out_dir=str(tmp_path),
                   ignore_errors=True)
        assert out["ok"] is True
        assert out["exportedWithErrors"] is True


class TestMigrate:
    def test_upgrades_a_v1_file(self):
        out = call("cardforge_migrate", path=MINIMAL)
        assert out["ok"] is True
        assert out["migrated"] is True
        assert out["document"]["cardforge"] == "2.0"

    def test_a_v2_document_passes_through_unmigrated(self):
        out = call("cardforge_migrate", document=doc())
        assert out["ok"] is True and out["migrated"] is False

    def test_saves_when_asked(self, tmp_path):
        target = tmp_path / "migrated.cardforge.json"
        out = call("cardforge_migrate", path=MINIMAL, save_to=str(target))
        assert out["savedTo"] == str(target)
        assert json.loads(target.read_text(encoding="utf-8"))["cardforge"] == "2.0"

    def test_rejects_a_foreign_document(self):
        out = call("cardforge_migrate", document={"hello": "world"})
        assert out["ok"] is False and out["stage"] == "detect"
