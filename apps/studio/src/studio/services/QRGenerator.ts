// QR Code generator — uses `qrcode` library via data URL for reliability

import QRCode from 'qrcode'

export { formatQRValue } from './QRFields'
export type { QRType } from './QRFields'

/** Generate QR as SVG with quiet zone and material background */
export async function renderQRSVG(
  text: string,
  sizeMM: number,
  quietZoneMM: number = 2,
  pxPerMM: number = 4,
  backgroundColor: string = '#ffffff',  // material-compatible
  foregroundColor: string = '#000000',
): Promise<string> {
  const totalPx = sizeMM * pxPerMM
  const qzPx = quietZoneMM * pxPerMM

  // Generate QR with standard quiet zone built-in (4 modules of margin)
  const dataUrl = await QRCode.toDataURL(text || 'cardforge', {
    errorCorrectionLevel: 'M',
    margin: 4,  // standard QR spec quiet zone = 4 modules
    width: Math.round(totalPx),
    color: { dark: foregroundColor, light: '#ffffff' },
  })

  // Background rect with material color (covers the whole QR area)
  const bg = `<rect x="0" y="0" width="${totalPx}" height="${totalPx}" fill="${backgroundColor}"/>`
  
  // White inner rect for quiet zone + QR white modules
  const inner = `<rect x="${qzPx}" y="${qzPx}" width="${sizeMM * pxPerMM - 2 * qzPx}" height="${sizeMM * pxPerMM - 2 * qzPx}" fill="white"/>`
  
  // QR image (has its own quiet zone built-in from margin:4)
  const qr = `<image href="${dataUrl}" x="0" y="0" width="${totalPx}" height="${totalPx}" preserveAspectRatio="none"/>`

  return bg + inner + qr
}
