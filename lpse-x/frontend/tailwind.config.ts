import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Existing risk colors - DO NOT CHANGE
        aman: '#22c55e',
        pantauan: '#f59e0b',
        tinggi: '#ef4444',
        kritis: '#7c2d12',
        // Forensic color scale (dark blues for AI forensics theme)
        forensic: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
        },
        // Surface tokens for dark UI
        surface: {
          dark:  '#020617',   // slate-950
          card:  '#1e293b',   // slate-800
          hover: '#334155',   // slate-700
        },
        // Accent tokens
        accent: {
          blue:  '#3b82f6',
          cyan:  '#06b6d4',
          amber: '#f59e0b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'card':       '0 1px 3px 0 rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.4)',
        'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.5), 0 2px 4px -2px rgb(0 0 0 / 0.5)',
        'glow-blue':  '0 0 12px 2px rgb(59 130 246 / 0.25)',
      },
      borderRadius: {
        card: '0.75rem',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.6' },
        },
      },
      animation: {
        'fade-in':     'fadeIn 0.3s ease-out',
        'slide-up':    'slideUp 0.3s ease-out',
        'pulse-subtle':'pulse-subtle 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}

export default config
