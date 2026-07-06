/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["'Playfair Display'", "Georgia", "serif"],
        body: ["'DM Sans'", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        ink: {
          950: "#0A0C0F",
          900: "#111318",
          800: "#1A1E26",
          700: "#242934",
          600: "#2F3645",
          500: "#3D4558",
          400: "#6B7591",
          300: "#9AA3B8",
          200: "#C5CBDA",
          100: "#E8EBF2",
          50: "#F5F6FA",
        },
        gold: {
          600: "#B8860B",
          500: "#D4A017",
          400: "#E8B930",
          300: "#F5CC55",
          200: "#FAE08A",
          100: "#FDF3CC",
        },
        jade: {
          700: "#064E3B",
          600: "#065F46",
          500: "#047857",
          400: "#059669",
          300: "#34D399",
          100: "#D1FAE5",
        },
        ruby: {
          700: "#9B1C1C",
          600: "#B91C1C",
          500: "#DC2626",
          400: "#EF4444",
          100: "#FEE2E2",
        },
        azure: {
          600: "#1E40AF",
          500: "#2563EB",
          400: "#3B82F6",
          300: "#93C5FD",
          100: "#DBEAFE",
        },
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out",
        "slide-up": "slideUp 0.35s cubic-bezier(0.16, 1, 0.3, 1)",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        shimmer: "shimmer 1.8s linear infinite",
        "spin-slow": "spin 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(12px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "noise": "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
};
