// tailwind.config.js
// Tailwind CSS configuration for the Helix dashboard.
// Extends the default theme with the Helix brand design system.

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        helix: {
          bg:       '#0c0c0e',
          canvas:   '#0c0c0e',
          surface:  '#161618',
          panel:    'rgba(22, 22, 24, 0.92)',
          border:   'rgba(255, 255, 255, 0.08)',
          brand:    '#E61919',
          primary:  '#E61919',
          success:  '#22C55E',
          error:    '#E61919',
          warning:  '#F59E0B',
          textPrimary: '#F1F0FF',
          textMuted:   '#9CA3AF',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'helix-glow': '0 0 0 1px rgba(230, 25, 25, 0.35), 0 8px 32px rgba(230, 25, 25, 0.1)',
        'helix-card': '0 4px 24px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.06)',
        'helix-panel': '0 24px 48px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(255, 255, 255, 0.08)',
        'helix-float': '0 8px 32px rgba(0, 0, 0, 0.4)',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'spin-slow': 'spin 2s linear infinite',
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 0 1px rgba(230, 25, 25, 0.2)' },
          '50%':       { boxShadow: '0 0 0 2px rgba(230, 25, 25, 0.45), 0 0 20px rgba(230, 25, 25, 0.15)' },
        },
      },
    },
  },
  plugins: [],
}
