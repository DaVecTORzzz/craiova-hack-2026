// SafeTarmac AI - Tokeni Canonici Design System (Conform 03_C_frontend.pdf)

export const THEME_CONFIG = {
  // Paleta Dark Mode (Command Center Deck)
  dark: {
    appBg: '#292929',
    panelBg: '#352F6B',
    panelBorder: 'rgba(255, 255, 255, 0.08)',
    accentColor: '#5448C8',
    accentHover: '#3F34A8',
    textColor: '#FFFFFF',
    textMuted: '#CBD5E1',
    cardBg: 'rgba(41, 41, 41, 0.6)',
    cardHover: 'rgba(41, 41, 41, 0.85)',
    inputBg: '#292929',
    badgeBg: 'rgba(84, 72, 200, 0.35)',
    modalOverlay: 'rgba(0, 0, 0, 0.85)'
  },
  // Paleta Light Mode (Conformă tokenilor Neutru #EBEBEB / #B3F1B2)
  light: {
    appBg: '#EBEBEB',
    panelBg: '#B3F1B2',
    panelBorder: 'rgba(0, 0, 0, 0.08)',
    accentColor: '#5448C8',
    accentHover: '#3F34A8',
    textColor: '#292929',
    textMuted: '#555555',
    cardBg: 'rgba(255, 255, 255, 0.75)',
    cardHover: 'rgba(255, 255, 255, 0.95)',
    inputBg: '#FFFFFF',
    badgeBg: 'rgba(112, 237, 110, 0.45)',
    modalOverlay: 'rgba(15, 23, 42, 0.6)'
  }
};

// Tokeni oficiali de stare și severitate (Decizie Canonică N06):
// Severitate: doar CRITICAL sau WARNING
// Stare: open, acknowledged, false_positive, escalated, resolved
export const STATUS_TOKENS = {
  // Severitate
  CRITICAL: {
    bg: '#FBF0EF',
    text: '#8E1F19',
    border: '#EFC7C3',
    dot: '#E5484D',
    label: 'CRITICAL'
  },
  WARNING: {
    bg: '#FCF5E8',
    text: '#7F4A06',
    border: '#E9D2A6',
    dot: '#F5A524',
    label: 'WARNING'
  },
  // Stări
  open: {
    bg: '#FEF2F2',
    text: '#991B1B',
    border: '#FECACA',
    label: 'Deschis'
  },
  acknowledged: {
    bg: '#E3FBE3',
    text: '#1D6A1C',
    border: '#70ED6E',
    label: 'Confirmat (Ack)'
  },
  false_positive: {
    bg: '#F1F5F9',
    text: '#475569',
    border: '#CBD5E1',
    label: 'Fals Pozitiv'
  },
  escalated: {
    bg: '#FEE2E2',
    text: '#B91C1C',
    border: '#EF4444',
    label: 'Escaladat (Urgență)'
  },
  resolved: {
    bg: '#E3FBE3',
    text: '#1D6A1C',
    border: '#70ED6E',
    label: 'Rezolvat'
  }
};
