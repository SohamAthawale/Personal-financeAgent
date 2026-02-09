/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Sora', 'ui-sans-serif', 'system-ui'],
        body: ['DM Sans', 'ui-sans-serif', 'system-ui'],
      },
      colors: {
        ink: 'hsl(var(--ink))',
        muted: 'hsl(var(--muted))',
        line: 'hsl(var(--line))',
        surface: 'hsl(var(--surface))',
        'surface-muted': 'hsl(var(--surface-muted))',
        primary: 'hsl(var(--primary))',
        'primary-strong': 'hsl(var(--primary-strong))',
        accent: 'hsl(var(--accent))',
        'accent-strong': 'hsl(var(--accent-strong))',
        success: 'hsl(var(--success))',
        warning: 'hsl(var(--warning))',
        danger: 'hsl(var(--danger))',
      },
      boxShadow: {
        soft: '0 24px 60px -40px rgba(15, 23, 42, 0.65)',
        lift: '0 18px 40px -24px rgba(15, 23, 42, 0.6)',
      },
    },
  },
  plugins: [],
};
