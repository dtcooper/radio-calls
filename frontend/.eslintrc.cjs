/** @type { import("eslint").Linter.Config } */
module.exports = {
  root: true,
  extends: ["eslint:recommended", "plugin:svelte/recommended", "prettier"],
  parserOptions: {
    sourceType: "module",
    ecmaVersion: 2020,
    extraFileExtensions: [".svelte"]
  },
  ignorePatterns: ["build/**"],
  env: {
    browser: true,
    es2017: true,
    node: true
  }
}
