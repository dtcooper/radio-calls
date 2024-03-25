import { sveltekit } from "@sveltejs/kit/vite"
import { defineConfig } from "vite"

const backendUrlsToProxy = ["api", "backend-static", "cmsadmin"]

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: Object.fromEntries(backendUrlsToProxy.map((url) => [`/${url}`, "http://localhost:8000"]))
  }
})
