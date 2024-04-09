import { sveltekit } from "@sveltejs/kit/vite"
import { execSync } from "child_process"
import { existsSync, readFileSync, writeFileSync } from "fs"
import { defineConfig } from "vite"

const backendUrlsToProxy = ["api", "backend-static", "cmsadmin", "__debug__"]
const addVersionString = () => {
  try {
    const indexPath = "build/index.html"
    if (execSync(indexPath)) {
      const gitDir = `${__dirname}/../.git`
      let version = "unknown"
      if (existsSync(gitDir)) {
        version = execSync(`git --git-dir=${gitDir} --short=8 rev-parse HEAD`, { encoding: "utf-8" }).trim()
      }
      const html = readFileSync(indexPath, { encoding: "utf-8" })
      const newHtml = html.replace(">>>VERSION<<<", version).replace(">>>BUILD_TIME<<<", new Date())

      writeFileSync(indexPath, newHtml, { encoding: "utf-8" })
    }
  } catch (e) {
    console.warn("Error getting version during build", e)
  }
}

export default defineConfig({
  plugins: [sveltekit(), { name: "add-version", closeBundle: addVersionString }],
  server: {
    proxy: Object.fromEntries(
      backendUrlsToProxy.map((url) => [`/${url}`, { target: "http://localhost:8000", changeOrigin: false }])
    )
  }
})
