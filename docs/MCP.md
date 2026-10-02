# CardForge MCP Server

> Drive the compiler from an AI agent.

CardForge's document format is declarative JSON with a strict schema, and its
manufacturing analyzer already answers the question *"will this print, and if
not, what should I change?"* in structured form. That combination is what makes
the compiler agent-operable: a model can author a document, get a verdict it can
parse, and repair the design without a human in the loop.

The MCP server exposes that loop. It runs the kernel **in-process** — no HTTP
server, no port, no CORS — over the same `cardforge.service` path the Studio
uses, so an agent and a human see identical constraints, scores and geometry.

## Install

```bash
uv sync --extra mcp
```

## Register

The repo ships a project-scoped [`.mcp.json`](../.mcp.json), so any MCP client
that reads it (Claude Code among them) picks the server up when the project root
is CardForge. To register it from elsewhere:

```bash
claude mcp add cardforge -- uv run --directory /path/to/CardForge python -m cardforge.mcp_server
```

Or run it directly for debugging:

```bash
uv run python -m cardforge.mcp_server   # speaks MCP over stdio
```

## Tools

| Tool | Purpose |
|------|---------|
| `cardforge_guide` | Authoring rules: units, coordinate convention, workflow, every feature type with its required fields. **Read first.** |
| `cardforge_examples` | Known-good documents to start from, each with its compile verdict. |
| `cardforge_schema` | The raw v2 JSON Schema — `section="features"` (compact) or `"full"`. |
| `cardforge_fonts` | Families the kernel can actually render on this machine. |
| `cardforge_compile` | Compile and get the verdict, the issues with fix suggestions, and per-feature bounds in mm. |
| `cardforge_export` | Write the manufacturing package (3MF + per-material STLs + report). |
| `cardforge_migrate` | Normalize a legacy v1 document to validated v2. |

Every tool takes the document either inline (`document`) or from disk (`path`),
never both.

## The verdict — the only stopping condition

**Use `verdict.ready`. Do not stop on `manufacturing.score` or
`manufacturing.errorCount`.**

A compile reports problems through three channels, and none is a superset of
the others:

| Channel | What it knows |
|---------|---------------|
| `constraints` (kernel) | Geometry the compiler cannot honour as authored |
| `manufacturing` (analyzer) | Whether it survives the printer |
| `warnings` / `skippedFeatures` (trace) | What the compiler changed or dropped while building |

The manufacturing score only sees its own channel. That is not a rounding
error — it is the difference between shipping and not:

```
Back-face emboss:  score 100, "Excellent — ready to print", errorCount 0
                   …and the back of the card is completely blank,
                   because emboss is refused on the bed-facing face
                   and the feature produced no geometry at all.

Pocket too deep:   score 100, "Excellent — ready to print", errorCount 0
                   …and the cavity punches through the body.
```

Both are caught by `constraints`, and `cardforge_export` correctly refuses
both. But an agent whose loop reads "score 100, no errors" stops early and
reports success on a blank card.

`verdict` unifies all three channels into one answer:

```json
{
  "ready": false,
  "summary": "Not ready — 1 blocker(s). Fix these before exporting: back-emboss-not-flat",
  "blockers": [{ "source": "constraint", "code": "back-emboss-not-flat",
                 "featureId": "qr", "message": "…", "suggestion": "…" }],
  "warnings": [ … ]
}
```

A **skipped feature is always a blocker**, even when every rule the analyzer
knows is satisfied: the caller asked for something and the model does not
contain it. That is the quietest way a prompt-driven run fails.

`blockers[].source` names the channel that spoke, so a geometry refusal is
distinguishable from a printability complaint.

## Design constraints

**No geometry crosses the wire.** A mesh is unreadable to a model and would
consume its context for nothing. `cardforge_compile` returns the verdict and the
measurements; the 3MF only reaches disk, and only when the caller passes
`save_3mf_to`. A test enforces this — the compile result stays under 20 KB of
JSON.

**Failures are structured, not raised.** Every tool returns `{ok: false, stage,
error}` rather than throwing, so a model always gets something it can act on.
`stage` says where it broke — `input`, `validation`, `load`, `compile`,
`blocked`, `write` — which is usually enough to pick the next move. A validation
failure also carries a `hint` pointing at `cardforge_schema`.

**The guide is generated from the schema.** Feature types and their required
fields are read out of `v2.schema.json` at call time, so a new feature type
cannot silently go undocumented. A test asserts the guide covers all eight.

**`featureBounds` makes layout checkable by arithmetic.** Each compile reports
where every feature actually landed in document space (top-left origin, y down,
mm) — the same frame the document is authored in. That lets an agent verify
margins and overlaps without rendering anything. The HTTP API returns the same
array.

## The repair loop

This is the whole point. Compile, read the blockers, apply their suggestions,
recompile — until `verdict.ready`. From the prompt *"tarjeta hito.uno, negra
con blanco, nombre y rol adelante, QR al dorso, bolsillo para tag NFC"*:

```
INTENTO 1: ready=False | Not ready — 1 blocker(s): back-emboss-not-flat
   BLOQUEA back-emboss-not-flat (qr)
      fix: QR on the back — emboss → flush (white inlay, face stays flat)
INTENTO 2: ready=True  | Ready. 1 warning(s), manufacturing score 95/100.

export -> 3MF + 2 STLs + report
```

Two iterations, no human in the loop. The domain knowledge lives in
`manufacturing/rules.py` and `kernel/constraints.py`, not in the agent's
prompt: a model does not need to know anything about FDM printing to
converge — it needs to read a `suggestion` and edit JSON.

Geometry can then be verified by arithmetic rather than by eye. The NFC pocket
above, checked by differencing the base volume with and without it:

```
material removed  :  497.96 mm3
expected cylinder :  498.76 mm3   (Ø25.2 x 1.0mm)
difference        :  0.2%         (circle faceting)
floor under tag   :  0.8 mm       (minimum 0.8)
```

## Coordinate convention

Worth stating once, because it is the thing most easily got wrong:

- Every length is **millimetres**; angles are degrees.
- Document space has its origin at the **top-left** of the face, y pointing
  **down**.
- `transform.x` / `transform.y` is the feature's **top-left corner**, not its
  centre. A `shape` at `{x: 10, y: 10}` sized 20×8 occupies x 10..30, y 10..18.
- A QR's anchor includes its quiet zone, so the printed modules start at
  `x + quietZone` (2 mm by default).
- Back-face features are authored in back-face document space and mirrored by
  the compiler — author the back as if looking straight at it.

## Known gap

The agent can verify that a design *prints*; it cannot see whether it *looks
good*. There is no server-side rasterizer, so nothing returns an image. A
`POST /api/render` producing a PNG per face would close the visual half of the
loop and let a model critique its own layout. Until then, the numbers in
`featureBounds` are the only spatial feedback available.
