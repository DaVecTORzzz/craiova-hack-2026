// SafeSight - Design System & Tokeni Oficiali
// Conform cerințelor de semnalizare industrială și paletei Coolors oficiale:
// Carbon Black (#1F1F1F), Scarlet Rush (#D73833), Bright Lemon (#FFEB33), Frosted Blue (#7EDEED), White Smoke (#F5F5F5)

export const THEME_CONFIG = {
  // Paleta Dark Mode (Veritabil Dark Mode pentru consolă de control aeroportuar)
  dark: {
    appBg: '#1F1F1F',           // Carbon Black oficial Coolors
    panelBg: '#272727',         // Panou neutru profund cu contrast ridicat
    panelBorder: 'rgba(255, 255, 255, 0.10)',
    navBg: '#141414',           // Antracit profund / bleumarin autoritar foarte închis
    navBorder: 'rgba(255, 255, 255, 0.12)',
    accentColor: '#1976D2',     // Albastru industrial
    accentHover: '#1565C0',
    textColor: '#F8FAFC',       // Contrast WCAG > 7:1
    textMuted: '#A3A3A3',       // Gri neutru lizibil
    cardBg: '#2A2A2A',          // Fundal carduri neutru
    cardHover: '#333333',
    inputBg: '#171717',
    badgeBg: 'rgba(126, 222, 237, 0.18)', // Frosted blue badge
    modalOverlay: 'rgba(0, 0, 0, 0.85)'
  },
  // Paleta Light Mode (Pânză curată White Smoke conform Coolors cu text Carbon Black)
  light: {
    appBg: '#F5F5F5',           // White Smoke oficial Coolors
    panelBg: '#FFFFFF',         // Alb curat
    panelBorder: '#E5E7EB',
    navBg: '#0D47A1',           // Bleumarin autoritar pentru navigare
    navBorder: 'rgba(255, 255, 255, 0.15)',
    accentColor: '#1976D2',     // Albastru industrial
    accentHover: '#1565C0',
    textColor: '#1F1F1F',       // Carbon Black oficial (WCAG > 10:1)
    textMuted: '#666666',       // Gri neutru lizibil
    cardBg: '#FFFFFF',
    cardHover: '#F8FAFC',
    inputBg: '#FAFAFA',
    badgeBg: 'rgba(25, 118, 210, 0.12)',
    modalOverlay: 'rgba(15, 23, 42, 0.65)'
  }
};

// Culori de Semnalizare Industrială & Aeroportuară (Folosite EXCLUSIV pentru status, acțiuni și alerte)
export const SIGNAL_COLORS = {
  RED_CRITICAL: '#D73833',      // Scarlet Rush oficial Coolors (incidente critice, pericol major, oprire)
  AMBER_WARNING: '#FFEB33',     // Bright Lemon oficial Coolors (avertismente, zone împiedicare, vehicule în mișcare)
  GREEN_SAFE: '#388E3C',        // Condiții sigure, prim-ajutor, confirmări (Verificare completă)
  BLUE_MANDATORY: '#1976D2',    // Acțiuni obligatorii, EIP (vestă, căști antifonice)
  FROSTED_BLUE: '#7EDEED'       // Frosted Blue oficial Coolors (informare, highlight tactil)
};

// Tokeni oficiali de stare și severitate (Decizie Canonică N06)
export const STATUS_TOKENS = {
  // Severitate
  CRITICAL: {
    color: '#D73833',
    bg: '#FEF2F2',
    bgDark: 'rgba(215, 56, 51, 0.22)',
    text: '#991B1B',
    textDark: '#FF8A80',
    border: '#D73833',
    borderDark: 'rgba(215, 56, 51, 0.60)',
    dot: '#D73833',
    label: 'CRITICAL'
  },
  WARNING: {
    color: '#FFEB33',
    bg: '#FFFBEB',
    bgDark: 'rgba(255, 235, 51, 0.18)',
    text: '#1F1F1F',
    textDark: '#FFEB33',
    border: '#FFEB33',
    borderDark: 'rgba(255, 235, 51, 0.60)',
    dot: '#FFEB33',
    label: 'WARNING'
  },
  // Stări Human-In-The-Loop
  open: {
    color: '#D73833',
    bg: '#FEF2F2',
    bgDark: 'rgba(215, 56, 51, 0.20)',
    text: '#991B1B',
    textDark: '#FF8A80',
    border: '#D73833',
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
    color: '#D73833',
    bg: '#FEE2E2',
    bgDark: 'rgba(215, 56, 51, 0.30)',
    text: '#991B1B',
    textDark: '#FF8A80',
    border: '#D73833',
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
