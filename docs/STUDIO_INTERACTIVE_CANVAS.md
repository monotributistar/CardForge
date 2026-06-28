# CardForge Studio — Interactive Canvas v0 (MVP-004)

## Overview

The Canvas is now interactive. Features can be selected with a click, show bounding boxes, and can be dragged to new positions. All edits go through the Document → Command → Compile flow.

## Key Principle

> The Canvas does NOT modify Geometry IR. The Canvas does NOT modify SVG.
> The Canvas executes Commands that modify the Document, then recompiles.

## Flow

```
Pointer Event → Canvas
  → SelectFeature or MoveFeature
  → Document position updated
  → CoreClient.preview() (or CompileService fallback)
  → SVG regenerated
  → Manufacturing score updated
  → UI reflects new state
```

## Coordinate System

- **Document:** mm, top-left origin, card bounds 0..w × 0..h
- **Screen:** pixels, top-left origin, zoom applied

Helpers in `CanvasCoords.ts`:
- `documentToScreen(docX, docY, ...)` → screen px
- `screenToDocument(screenX, screenY, ...)` → document mm
- `getFeatureBounds(feature)` → {x, y, w, h} in mm

## Selection

- Click on a feature → bounding box appears (blue border)
- Click on canvas background → deselect
- Selected feature shows semi-transparent highlight
- Inspector syncs to show selected feature properties

## Drag/Move

- `pointerdown` on bounding box → capture
- `pointermove` → convert screen px to document mm, update position optimistically
- `pointerup` → recompile preview + manufacturing

Position is clamped to card bounds. Rounded to 0.1mm.

## MoveFeatureCommand

```typescript
new MoveFeatureCommand(doc, featureId, toX, toY, onChange)
```

Saves `fromPosition` for future undo. Modifies `feature.position` in-place on the document.

## What's NOT implemented

- Resize handles
- Rotation
- Snap/grid
- Multi-select
- Copy/paste
- Keyboard shortcuts
- Undo/redo (command saves fromPosition, but undo not yet wired)

## Files

```
studio/canvas/
├── CanvasCoords.ts        # documentToScreen, screenToDocument, getFeatureBounds
├── MoveFeatureCommand.ts  # MoveFeatureCommand
├── InteractiveCanvas.tsx  # SVG + selection overlay + pointer events
├── Canvas.tsx             # Original Canvas (kept for fallback)
```
