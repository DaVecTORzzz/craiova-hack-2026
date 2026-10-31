// SafeSight - Design System & Tokeni Oficiali
// Conform cerințelor de semnalizare industrială și autoritate aeroportuară

export const THEME_CONFIG = {
  // Paleta Dark Mode (Veritabil Dark Mode pentru consolă de control aeroportuar)
  dark: {
    appBg: '#121212',           // Gri antracit profund / aproape negru
    panelBg: '#1A1F2C',         // Panou neutru profund cu contrast ridicat
    panelBorder: 'rgba(255, 255, 255, 0.09)',
    navBg: '#0A1128',           // Bleumarin autoritar foarte închis pentru Header & Sidebar
    navBorder: 'rgba(255, 255, 255, 0.1)',
    accentColor: '#1976D2',     // Albastru industrial / acțiuni obligatorii
    accentHover: '#1565C0',
    textColor: '#F8FAFC',       // Contrast WCAG > 7:1
    textMuted: '#94A3B8',       // Gri neutru lizibil
    cardBg: '#1E2433',          // Fundal carduri neutru
    cardHover: '#262D40',
    inputBg: '#0F172A',
    badgeBg: 'rgba(25, 118, 210, 0.25)',
    modalOverlay: 'rgba(0, 0, 0, 0.85)'
  },
  // Paleta Light Mode (Pânză curată, alb și gri deschis cu bleumarin profesional)
  light: {
    appBg: '#F5F5F5',           // White Smoke neutru
    panelBg: '#FFFFFF',         // Alb curat
    panelBorder: '#E2E8F0',
    navBg: '#0D47A1',           // Bleumarin autoritar pentru navigare
    navBorder: 'rgba(255, 255, 255, 0.15)',
    accentColor: '#1976D2',     // Albastru industrial
    accentHover: '#1565C0',
    textColor: '#212121',       // Gri Antracit / Aproape Negru (WCAG > 10:1, reduce oboseala)
    textMuted: '#616161',       // Gri neutru lizibil
    cardBg: '#FFFFFF',
    cardHover: '#F8FAFC',
    inputBg: '#F8FAFC',
    badgeBg: 'rgba(25, 118, 210, 0.12)',
    modalOverlay: 'rgba(15, 23, 42, 0.65)'
  }
};

// Culori de Semnalizare Industrială & Aeroportuară (Folosite EXCLUSIV pentru status, acțiuni și alerte)
export const SIGNAL_COLORS = {
  RED_CRITICAL: '#D32F2F',      // Incidente critice, pericol major, oprire de urgență
  AMBER_WARNING: '#FFC107',     // Avertismente, zone împiedicare, vehicule în mișcare
  GREEN_SAFE: '#388E3C',        // Condiții sigure, prim-ajutor, confirmări (Verificare completă)
  BLUE_MANDATORY: '#1976D2'     // Acțiuni obligatorii, EIP (vestă, căști antifonice)
};

// Tokeni oficiali de stare și severitate (Decizie Canonică N06)
export const STATUS_TOKENS = {
  // Severitate
  CRITICAL: {
    color: '#D32F2F',
    bg: '#FEF2F2',
    bgDark: 'rgba(211, 47, 47, 0.18)',
    text: '#B71C1C',
    textDark: '#EF5350',
    border: '#FFCDD2',
    borderDark: 'rgba(211, 47, 47, 0.45)',
    dot: '#D32F2F',
    label: 'CRITICAL'
  },
  WARNING: {
    color: '#FFC107',
    bg: '#FFFBEB',
    bgDark: 'rgba(255, 193, 7, 0.16)',
    text: '#B45309',
    textDark: '#FFD54F',
    border: '#FDE68A',
    borderDark: 'rgba(255, 193, 7, 0.45)',
    dot: '#FFC107',
    label: 'WARNING'
  },
  // Stări Human-In-The-Loop
  open: {
    color: '#D32F2F',
    bg: '#FEF2F2',
    bgDark: 'rgba(211, 47, 47, 0.15)',
    text: '#B71C1C',
    textDark: '#EF5350',
    border: '#FECACA',
    label: 'Deschis'
  },
  acknowledged: {
    color: '#388E3C',
    bg: '#F0FDF4',
    bgDark: 'rgba(56, 142, 60, 0.18)',
    text: '#1B5E20',
    textDark: '#81C784',
    border: '#A7F3D0',
    label: 'Confirmat (Ack)'
  },
  false_positive: {
    color: '#64748B',
    bg: '#F1F5F9',
    bgDark: 'rgba(100, 116, 139, 0.18)',
    text: '#334155',
    textDark: '#94A3B8',
    border: '#CBD5E1',
    label: 'Fals Pozitiv'
  },
  escalated: {
    color: '#D32F2F',
    bg: '#FEE2E2',
    bgDark: 'rgba(211, 47, 47, 0.25)',
    text: '#991B1B',
    textDark: '#FF8A80',
    border: '#EF4444',
    label: 'Escaladat (Urgență)'
  },
  resolved: {
    color: '#388E3C',
    bg: '#F0FDF4',
    bgDark: 'rgba(56, 142, 60, 0.18)',
    text: '#1B5E20',
    textDark: '#81C784',
    border: '#86EFAC',
    label: 'Rezolvat'
  }
};
