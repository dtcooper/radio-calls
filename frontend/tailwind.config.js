import daisyui from "daisyui"
import defaultTheme from "tailwindcss/defaultTheme"

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{html,js,svelte,ts}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Space Grotesk", ...defaultTheme.fontFamily.sans],
        mono: ["Space Mono", ...defaultTheme.fontFamily.mono]
      },
      animation: {
        "highlight-shadow": "highlight-shadow 1s cubic-bezier(0, 0, 0.3, 1) infinite"
      },
      keyframes: {
        "highlight-shadow": {
          "0%": {
            boxShadow: `0 0 0 0px var(--highlight-color, var(--tw-shadow-color, #000000))`
          },
          "90%": {
            boxShadow: `0 0 0 15px rgba(0, 0, 0, 0)`
          },
          "100%": {
            boxShadow: `0 0 0 0px rgba(0, 0, 0, 0)`
          }
        }
      }
    }
  },
  daisyui: {
    logs: false,
    darkTheme: "dark",
    themes: ["light", "dark"]
  },
  plugins: [daisyui]
}
