/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // <-- C'est ça qui dit à Tailwind de scanner tes fichiers React
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}