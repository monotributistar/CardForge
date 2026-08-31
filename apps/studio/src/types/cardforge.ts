// CardForge document model v2 — the wire format the Core validates.
//
// Units: mm. Origin: top-left of the object, y down.
// `material` on a feature references materials[].id.

export type Outline =
  | { type: 'rect'; width: number; height: number }
  | { type: 'rounded-rect'; width: number; height: number; radius: number; corners?: { tl?: number; tr?: number; br?: number; bl?: number } }
  | { type: 'circle'; diameter: number }
  // path: svgInline (full SVG markup — preferred) or svgPath (raw `d` data).
  // colorMap {svg hex → material id} extrudes each color in its own material
  // (multicolor base); unmapped regions print in base.
  // colorDepth limits the colors to a layer that deep on colorFace (default
  // 'front'), leaving base material behind it — so the other face is a clean
  // canvas for text/QR. Omit it and the colors run through the whole body.
  | { type: 'path'; svgPath: string; svgInline?: string; colorMap?: Record<string, string>; colorDepth?: number; colorFace?: 'front' | 'back' | 'both'; width: number; height: number }

export type Fill =
  | { type: 'solid' }
  | { type: 'lattice'; pattern: 'dots' | 'lines' | 'grid' | 'hex'; spacing: number; lineWidth?: number; border?: number }

export interface Backing { mode: 'auto' | 'on' | 'off'; thickness?: number; material?: string; padding?: number; shape?: 'rect' | 'circle' }

export interface DocumentV2 {
  cardforge: '2.0'
  meta: { id: string; name: string; description?: string; created?: string; modified?: string }
  object: {
    outline: Outline
    thickness: number
    fill?: Fill
  }
  materials: Material[]
  variables?: Record<string, string>
  assets?: Record<string, string>
  manufacturing?: { process?: 'fdm'|'sla'|'laser'|'cnc'; profile?: string; nozzle?: number; layerHeight?: number }
  faces: { front?: Face; back?: Face }
}
export interface Material { id: string; name: string; color: string; slot?: number; role?: 'base'|'text'|'accent'|'detail'|'support' }
export interface Face { features: Feature[] }
export type ReliefMode = 'emboss'|'deboss'|'flush'|'cut'|'deboss-backed'
export interface Relief { mode: ReliefMode; height?: number; depth?: number; floorMaterial?: string; floorThickness?: number }
export interface FontSpec { family: string; size: number; weight?: number; italic?: boolean; axes?: Record<string, number> }
export interface FeatureBase { id: string; type: string; name?: string; transform: { x: number; y: number; rotation?: number; scale?: number }; material: string; relief: Relief; zOrder?: number; visible?: boolean; backing?: Backing }
export interface TextBlockFeature extends FeatureBase { type: 'text-block'; lines: string[]; font: FontSpec; align?: 'left'|'center'|'right'; lineHeight?: number }
export interface TextPatternFeature extends FeatureBase { type: 'text-pattern'; text: string; font: FontSpec; spacing: number; spacingY?: number; angle?: number }
export interface PatternFeature extends FeatureBase { type: 'pattern'; patternType: 'dots'|'lines'|'grid'|'hex'|'svg'; spacing: number; spacingY?: number; angle?: number; elementSize?: number; region?: 'face'|'bounds'; width?: number; height?: number; svgInline?: string; colorMap?: Record<string, string> }
export interface QRFeature extends FeatureBase { type: 'qr'; qrType: 'url'|'vcard'|'wifi'|'email'|'text'; fields: Record<string, string>; size: number; errorCorrection?: 'L'|'M'|'Q'|'H'; quietZone?: number }
export interface IconFeature extends FeatureBase { type: 'icon'; svgAsset?: string; svgInline?: string; width: number; height?: number; colorMap?: Record<string, string> }
export interface ShapeFeature extends FeatureBase { type: 'shape'; shapeType: 'rect'|'rounded-rect'|'circle'|'ring'|'frame'|'corner-marks'|'path'; width?: number; height?: number; radius?: number; diameter?: number; strokeWidth?: number; inset?: number; length?: number; svgPath?: string }
// Hole — always a through-cut. circle (keyring) uses diameter; slot
// (lanyard/credential) uses width×height with full-radius ends. `tab` adds a
// material lug (hole dilated by tabMargin) fused into the base, so the hole
// can sit outside the outline.
export interface HoleFeature extends FeatureBase { type: 'hole'; holeType: 'circle'|'slot'; diameter?: number; width?: number; height?: number; tab?: boolean; tabMargin?: number }
// Pocket — a blind cavity sized to hold an insert (magnet, RFID/NFC tag).
// Cylindrical only for now. diameter/depth are the INSERT's nominal size; the
// cavity actually cut is (diameter + clearance) × (depth + depthClearance), so
// the fit is tuned without lying about what goes in it. `ceiling` is the lid
// left over the pocket, measured from the face: 0 opens it at the surface,
// anything more buries the insert (the print must pause to drop it in).
// Like a hole, a pocket owns its own z geometry and ignores `relief`. It
// ignores `transform.scale` too — the bore is measured from the insert, so
// scaling it would widen the bore and leave the depth alone. Resize via
// `diameter` (the canvas offers no scale handle on one).
export interface PocketFeature extends FeatureBase { type: 'pocket'; pocketType: 'circle'; insert?: 'magnet'|'rfid'|'other'; diameter: number; depth: number; clearance?: number; depthClearance?: number; ceiling?: number }
export type Feature = TextBlockFeature|TextPatternFeature|PatternFeature|QRFeature|IconFeature|ShapeFeature|HoleFeature|PocketFeature

/** Fit defaults, mirroring the Core (document/schema_v2.py). A printed bore
 *  comes out undersized, so an insert needs the cavity opened up to fit. */
export const DEFAULT_POCKET_CLEARANCE = 0.2
export const DEFAULT_POCKET_DEPTH_CLEARANCE = 0.1

export type FaceId = 'front' | 'back'
