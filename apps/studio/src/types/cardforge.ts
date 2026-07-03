// CardForge document model v2 — the wire format the Core validates.
//
// Units: mm. Origin: top-left of the object, y down.
// `material` on a feature references materials[].id.

export type Outline =
  | { type: 'rect'; width: number; height: number }
  | { type: 'rounded-rect'; width: number; height: number; radius: number; corners?: { tl?: number; tr?: number; br?: number; bl?: number } }
  | { type: 'circle'; diameter: number }
  | { type: 'path'; svgPath: string; width: number; height: number }

export type Fill =
  | { type: 'solid' }
  | { type: 'lattice'; pattern: 'dots' | 'lines' | 'grid' | 'hex'; spacing: number; lineWidth?: number; border?: number }

export interface Backing { mode: 'auto' | 'on' | 'off'; thickness?: number; material?: string }

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
export interface TextPatternFeature extends FeatureBase { type: 'text-pattern'; text: string; font: FontSpec; spacing: number; angle?: number }
export interface PatternFeature extends FeatureBase { type: 'pattern'; patternType: 'dots'|'lines'|'grid'|'hex'; spacing: number; angle?: number; elementSize?: number; region?: 'face'|'bounds'; width?: number; height?: number }
export interface QRFeature extends FeatureBase { type: 'qr'; qrType: 'url'|'vcard'|'wifi'|'email'|'text'; fields: Record<string, string>; size: number; errorCorrection?: 'L'|'M'|'Q'|'H'; quietZone?: number }
export interface IconFeature extends FeatureBase { type: 'icon'; svgAsset?: string; svgInline?: string; width: number; height?: number; colorMap?: Record<string, string> }
export interface ShapeFeature extends FeatureBase { type: 'shape'; shapeType: 'rect'|'rounded-rect'|'circle'|'ring'|'frame'|'corner-marks'|'path'; width?: number; height?: number; radius?: number; diameter?: number; strokeWidth?: number; inset?: number; length?: number; svgPath?: string }
export type Feature = TextBlockFeature|TextPatternFeature|PatternFeature|QRFeature|IconFeature|ShapeFeature

export type FaceId = 'front' | 'back'
