import { sveltekit } from "@sveltejs/kit/vite"
import { execSync } from "child_process"
import { existsSync, readFileSync, writeFileSync } from "fs"
import { defineConfig } from "vite"

const backendUrlsToProxy = ["api", "static", "cmsadmin", "__debug__"]
const addVersionString = () => {
  try {
    const indexPath = "build/index.html"
    if (existsSync(indexPath)) {
      const gitDir = `${__dirname}/../.git`
      let version = "unknown"
      if (existsSync(gitDir)) {
        version = execSync(`git --git-dir=${gitDir} rev-parse --short=8 HEAD`, { encoding: "utf-8" }).trim()
      }
      const html = readFileSync(indexPath, { encoding: "utf-8" })
      const newHtml = html.replace(">>>VERSION<<<", version).replace(">>>BUILD_TIME<<<", new Date())

      writeFileSync(indexPath, newHtml, { encoding: "utf-8" })
    }
  } catch (e) {
    console.warn("Error getting version/build date during build", e)
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
