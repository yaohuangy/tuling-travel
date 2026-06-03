/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef2ff',
          100: '#dce3fc',
          200: '#bcc7f9',
          300: '#9aa8f5',
          400: '#7d8ff0',
          500: '#6d82de',
          600: '#5c6ac4',
          700: '#4a55a0',
          800: '#39447d',
          900: '#2b335e',
        },
        accent: {
          400: '#a57fd8',
          500: '#8f71d8',
          600: '#8a67cf',
          700: '#6f52b8',
        },
      },
      fontFamily: {
        sans: ['"Microsoft YaHei"', '"PingFang SC"', '"Segoe UI"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
