// QR type-specific field metadata for the Inspector.
//
// Payload formatting lives in the Core — the Studio only stores
// `qrType` + `fields` (Record<string, string>) on the QR feature.

export type QRType = 'url' | 'vcard' | 'wifi' | 'email' | 'text'

export const QR_TYPE_LABELS: Record<QRType, string> = {
  url: 'URL / Link',
  vcard: 'vCard Contact',
  wifi: 'WiFi Network',
  email: 'Email',
  text: 'Plain Text',
}

export interface QRFieldDef {
  key: string
  label: string
  type: 'text' | 'textarea' | 'select'
  placeholder: string
  options?: string[]
}

export const FIELD_DEFS: Record<QRType, QRFieldDef[]> = {
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
    { key: 'wifi_encryption', label: 'Security', type: 'select', placeholder: '', options: ['WPA', 'WEP', 'nopass'] },
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
