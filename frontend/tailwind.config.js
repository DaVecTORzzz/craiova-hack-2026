/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        safesight: {
          carbon: '#1F1F1F',
          scarlet: '#D73833',
          lemon: '#FFEB33',
          frosted: '#7EDEED',
          smoke: '#F5F5F5',
        },
        dark: {
          bg: '#1F1F1F',
          panel: '#282828',
          card: '#2D2D2D',
          border: 'rgba(255, 255, 255, 0.10)',
          accent: '#7EDEED',
          accentHover: '#5ccedc'
        },
        light: {
          bg: '#F5F5F5',
          panel: '#FFFFFF',
          card: '#FFFFFF',
          border: '#E5E7EB',
          accent: '#7EDEED',
          accentHover: '#5ccedc'
        }
      },
      animation: {
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'ping-slow': 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite',
        'scanline': 'scanline 8s linear infinite',
      },
      keyframes: {
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(1000%)' },
        }
      }
    },
  },
  plugins: [],
}
