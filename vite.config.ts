/// <reference types="node" />
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";

const apiOrigin = `http://127.0.0.1:${process.env.STABX_PORT || "8000"}`;

export default defineConfig({
  // Vue 入口在 ui/；npm 依赖仍装在仓库根目录的 package.json / node_modules。
  root: "ui",
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./ui", import.meta.url)),
    },
  },
  plugins: [
    vue(),
    AutoImport({
      imports: ["vue", "vue-router", "pinia"],
      resolvers: [ElementPlusResolver()],
      dts: "auto-imports.d.ts",
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: "components.d.ts",
    }),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": apiOrigin,
      "/health": apiOrigin,
      "/ws": { target: apiOrigin.replace("http", "ws"), ws: true },
    },
  },
  build: {
    outDir: "../dist",
    emptyOutDir: true,
  },
});
