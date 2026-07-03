// Asset types definitions — guardas, esquinas, SVG decor, tramas

export interface AssetTemplate {
  id: string
  type: 'guard' | 'corner' | 'svg-decor' | 'trama' | 'frame'
  label: string
  description: string
}

export const ASSET_TEMPLATES: AssetTemplate[] = [
  { id: 'guard-thin', type: 'guard', label: 'Thin Guard', description: '1mm border line' },
  { id: 'guard-double', type: 'guard', label: 'Double Guard', description: 'Two-line border' },
  { id: 'corner-rounded', type: 'corner', label: 'Rounded Corners', description: 'Decorative corner accents' },
  { id: 'corner-diamond', type: 'corner', label: 'Diamond Corners', description: 'Diamond corner marks' },
  { id: 'trama-dots', type: 'trama', label: 'Dot Pattern', description: 'Repeating dot texture' },
  { id: 'trama-lines', type: 'trama', label: 'Line Pattern', description: 'Diagonal line texture' },
  { id: 'frame-thin', type: 'frame', label: 'Thin Frame', description: 'Rectangular frame border' },
  { id: 'frame-rounded', type: 'frame', label: 'Rounded Frame', description: 'Rounded rect frame' },
]

/** Create a feature object for an asset template */
export function createAssetFeature(template: AssetTemplate, faceId: string): any {
  const base: any = {
    id: `${template.id}-${Date.now()}`,
    type: template.type,
    material: 'accent',
    position: { x: 0, y: 0 },
    size: { width: 85, height: 54 },
    relief: { mode: 'emboss', height: 0.2 },
    zIndex: 0,
    face: faceId,
  }

  switch (template.type) {
    case 'guard':
      base.thickness = 1
      base.inset = 2
      break
    case 'corner':
      base.cornerSize = 6
      base.inset = 3
      break
    case 'frame':
      base.thickness = 1.5
      base.inset = 4
      base.radius = 4
      break
    case 'trama':
      base.spacing = 3
      base.rotation = 0
      base.opacity = 0.15
      break
    case 'svg-decor':
      base.svgContent = ''
      break
  }

  return base
}

/** Render an asset feature to SVG */
export function renderAssetSVG(feat: any, cardW: number, cardH: number, px: number, color: string): string {
  const w = cardW * px
  const h = cardH * px
  const t = (feat.thickness || 1) * px
  const inset = (feat.inset || 2) * px
  const r = (feat.radius || 0) * px

  switch (feat.type) {
    case 'guard':
      return `<rect x="${inset}" y="${inset}" width="${w - 2*inset}" height="${h - 2*inset}" fill="none" stroke="${color}" stroke-width="${t}" rx="${r}"/>`
    case 'guard-double':
    case 'double-guard':
      return `<rect x="${inset}" y="${inset}" width="${w - 2*inset}" height="${h - 2*inset}" fill="none" stroke="${color}" stroke-width="${t}" rx="${r}"/>
        <rect x="${inset+t*2}" y="${inset+t*2}" width="${w - 2*(inset+t*2)}" height="${h - 2*(inset+t*2)}" fill="none" stroke="${color}" stroke-width="${t*0.5}" rx="${r}"/>`
    case 'frame':
      return `<rect x="${inset}" y="${inset}" width="${w - 2*inset}" height="${h - 2*inset}" fill="none" stroke="${color}" stroke-width="${t}" rx="${r}"/>`
    case 'corner':
      const cs = (feat.cornerSize || 6) * px
      const co = inset
      const corners = [
        `M${co},${co+cs} L${co},${co} L${co+cs},${co}`,  // top-left
        `M${w-co-cs},${co} L${w-co},${co} L${w-co},${co+cs}`,  // top-right
        `M${w-co},${h-co-cs} L${w-co},${h-co} L${w-co-cs},${h-co}`,  // bottom-right
        `M${co+cs},${h-co} L${co},${h-co} L${co},${h-co-cs}`,  // bottom-left
      ]
      return corners.map(d => `<path d="${d}" fill="none" stroke="${color}" stroke-width="${t}" stroke-linecap="round"/>`).join('\n')
    case 'trama':
      const sp = (feat.spacing || 3) * px
      const op = feat.opacity || 0.1
      const rot = feat.rotation || 0
      let pattern = ''
      if (feat.id?.includes('dots')) {
        // Dot pattern
        for (let x = sp; x < w; x += sp) {
          for (let y = sp; y < h; y += sp) {
            pattern += `<circle cx="${x}" cy="${y}" r="${sp*0.15}" fill="${color}" opacity="${op}"/>`
          }
        }
      } else {
        // Line pattern
        for (let i = -h; i < w + h; i += sp) {
          pattern += `<line x1="${i}" y1="0" x2="${i-h}" y2="${h}" stroke="${color}" stroke-width="${t*0.5}" opacity="${op}"/>`
        }
      }
      return pattern
    case 'svg-decor':
      return feat.svgContent || ''
    default:
      return ''
  }
}
