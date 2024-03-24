import { sveltekit } from "@sveltejs/kit/vite"
import { defineConfig } from "vite"

const backendUrlsToProxy = ["api", "backend-static", "cmsadmin"]

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    host: "0.0.0.0",
    proxy: Object.fromEntries(
      backendUrlsToProxy.map((url) => [
        `/${url}`,
        {
          target: "http://backend:8000",
          changeOrigin: false
        }
      ])
    )
  }
})
