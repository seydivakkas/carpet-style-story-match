import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        carpet: {
          50: "#fbf8f5",
          100: "#f4ece3",
          200: "#e7d6c4",
          300: "#d7b99d",
          400: "#c49774",
          500: "#b57d54",
          600: "#a66847",
          700: "#8a523b",
          800: "#704334",
          900: "#5c382d",
          950: "#321c17",
        },
      },
    },
  },
  plugins: [],
};

export default config;
