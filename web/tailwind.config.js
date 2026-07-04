/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#5C35CC',
        secondary: '#FF9800',
      },
    },
  },
  plugins: [],
  darkMode: 'class',
}
