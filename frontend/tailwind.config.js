/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          '"PingFang SC"',
          '"Microsoft YaHei"',
          "sans-serif",
        ],
        prose: [
          '"Noto Serif SC"',
          '"Source Han Serif SC"',
          '"Songti SC"',
          "SimSun",
          "serif",
        ],
      },
      colors: {
        brand: {
          50: "#eef8f5",
          100: "#d7eee7",
          200: "#b0ddd0",
          500: "#16836d",
          600: "#126d5a",
          700: "#0d5849",
          800: "#0b473c",
          900: "#08372f",
        },
      },
      boxShadow: {
        panel:
          "0 1px 2px rgb(28 25 23 / 0.04), 0 8px 24px rgb(28 25 23 / 0.05)",
        dialog: "0 24px 70px rgb(28 25 23 / 0.24)",
      },
    },
  },
  plugins: [],
};
