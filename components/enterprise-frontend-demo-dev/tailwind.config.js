/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'primary-orange': '#FF6B35',
        'secondary-orange': '#FF8C42',
        'dark-bg': '#0D0D0D',
        'dark-card': '#1A1A1A',
        'dark-border': '#2A2A2A',
        'dark-hover': '#252525',
      },
    },
  },
  plugins: [],
}

