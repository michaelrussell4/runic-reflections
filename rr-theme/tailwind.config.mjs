/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Light mode colors
        primary: 'var(--color-primary)',
        'primary-alt': 'var(--color-primary-alt)',
        'bg-light': 'var(--color-bg-light)',
        'bg-lighter': 'var(--color-bg-lighter)',
        'bg-white': 'var(--color-bg-white)',
        'text-dark': 'var(--color-text-dark)',
        'text-darker': 'var(--color-text-darker)',
        'text-medium': 'var(--color-text-medium)',
        'border-subtle': 'var(--color-border-subtle)',
        'header-bg': 'var(--color-header-bg)',
        'footer-from': 'var(--color-footer-from)',
        'footer-to': 'var(--color-footer-to)',
      },
    },
  },
  plugins: [],
};
