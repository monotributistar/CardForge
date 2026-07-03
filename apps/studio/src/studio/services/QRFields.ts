// QR type-specific field definitions and formatters

export type QRType = 'url' | 'vcard' | 'wifi' | 'email' | 'text'

export interface QRFields {
  url?: string
  // vCard
  vcard_name?: string
  vcard_title?: string
  vcard_phone?: string
  vcard_email?: string
  vcard_website?: string
  // WiFi
  wifi_ssid?: string
  wifi_password?: string
  wifi_encryption?: 'WPA' | 'WEP' | 'nopass'
  // Email
  email_address?: string
  email_subject?: string
  email_body?: string
  // Text
  text?: string
}

export const QR_TYPE_LABELS: Record<QRType, string> = {
  url: 'URL / Link',
  vcard: 'vCard Contact',
  wifi: 'WiFi Network',
  email: 'Email',
  text: 'Plain Text',
}

export const FIELD_DEFS: Record<QRType, Array<{ key: string; label: string; type: string; placeholder: string }>> = {
  url: [
    { key: 'url', label: 'URL', type: 'text', placeholder: 'https://example.com' },
  ],
  vcard: [
    { key: 'vcard_name', label: 'Name', type: 'text', placeholder: 'Javier Rodriguez' },
    { key: 'vcard_title', label: 'Title', type: 'text', placeholder: 'Frontend Developer' },
    { key: 'vcard_phone', label: 'Phone', type: 'text', placeholder: '+54 351 123 4567' },
    { key: 'vcard_email', label: 'Email', type: 'text', placeholder: 'javier@example.com' },
    { key: 'vcard_website', label: 'Website', type: 'text', placeholder: 'https://example.com' },
  ],
  wifi: [
    { key: 'wifi_encryption', label: 'Security', type: 'select', placeholder: '' },
    { key: 'wifi_ssid', label: 'SSID', type: 'text', placeholder: 'MyWiFi' },
    { key: 'wifi_password', label: 'Password', type: 'text', placeholder: 'wifi password' },
  ],
  email: [
    { key: 'email_address', label: 'To', type: 'text', placeholder: 'you@example.com' },
    { key: 'email_subject', label: 'Subject', type: 'text', placeholder: 'Hello' },
    { key: 'email_body', label: 'Body', type: 'textarea', placeholder: 'Message text...' },
  ],
  text: [
    { key: 'text', label: 'Text', type: 'textarea', placeholder: 'Any text to encode' },
  ],
}

/** Format QR content from type + fields */
export function formatQRValue(type: QRType, fields: QRFields): string {
  switch (type) {
    case 'url':
      const u = fields.url || ''
      return u.startsWith('http') ? u : u ? `https://${u}` : 'https://cardforge.app'
    case 'vcard':
      return [
        'BEGIN:VCARD', 'VERSION:3.0',
        `FN:${fields.vcard_name || ''}`,
        fields.vcard_title ? `TITLE:${fields.vcard_title}` : '',
        fields.vcard_phone ? `TEL:${fields.vcard_phone}` : '',
        fields.vcard_email ? `EMAIL:${fields.vcard_email}` : '',
        fields.vcard_website ? `URL:${fields.vcard_website}` : '',
        'END:VCARD',
      ].filter(l => !l.endsWith(':')).join('\n')
    case 'wifi':
      const enc = fields.wifi_encryption || 'WPA'
      return `WIFI:T:${enc};S:${fields.wifi_ssid || ''};P:${fields.wifi_password || ''};;`
    case 'email':
      let mail = `mailto:${fields.email_address || ''}`
      const params: string[] = []
      if (fields.email_subject) params.push(`subject=${encodeURIComponent(fields.email_subject)}`)
      if (fields.email_body) params.push(`body=${encodeURIComponent(fields.email_body)}`)
      if (params.length) mail += '?' + params.join('&')
      return mail
    case 'text':
      return fields.text || ''
    default:
      return ''
  }
}

/** Extract QR fields from a feature's stored properties */
export function getQRFields(feature: any): QRFields {
  return {
    url: feature?.url,
    vcard_name: feature?.vcard_name,
    vcard_title: feature?.vcard_title,
    vcard_phone: feature?.vcard_phone,
    vcard_email: feature?.vcard_email,
    vcard_website: feature?.vcard_website,
    wifi_ssid: feature?.wifi_ssid,
    wifi_password: feature?.wifi_password,
    wifi_encryption: feature?.wifi_encryption || 'WPA',
    email_address: feature?.email_address,
    email_subject: feature?.email_subject,
    email_body: feature?.email_body,
    text: feature?.text || feature?.value,
  }
}
