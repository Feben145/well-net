/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Well-Net brand palette
        wellnet: {
          50:  "#E1F5EE",
          100: "#C3EBD8",
          200: "#9FE1CB",
          300: "#5DCAA5",
          400: "#2DB887",
          500: "#1D9E75",  // primary
          600: "#158560",
          700: "#0F6E50",
          800: "#085041",
          900: "#04342C",
        },
        amber: {
          50:  "#FAEEDA",
          100: "#F5DDB5",
          200: "#EFC17A",
          500: "#EF9F27",  // accent amber
          700: "#BA7517",
          900: "#633806",
        },
        coral: {
          50:  "#FAECE7",
          500: "#E05C3A",
          900: "#712B13",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
        "3xl": "1.5rem",
      },
      animation: {
        "score-in": "scoreIn 0.8s ease-out",
        "fade-up": "fadeUp 0.4s ease-out",
        "slide-in": "slideIn 0.3s ease-out",
      },
      keyframes: {
        scoreIn: {
          "0%":   { "stroke-dashoffset": "157" },
          "100%": { "stroke-dashoffset": "var(--offset)" },
        },
        fadeUp: {
          "0%":   { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%":   { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
    },
  },
  plugins: [],
}
