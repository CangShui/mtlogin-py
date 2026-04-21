/// <reference types="vitest/config" />

import { resolve } from "node:path"
import vue from "@vitejs/plugin-vue"
import UnoCSS from "unocss/vite"
import AutoImport from "unplugin-auto-import/vite"
import SvgComponent from "unplugin-svg-component/vite"
import { ElementPlusResolver } from "unplugin-vue-components/resolvers"
import Components from "unplugin-vue-components/vite"
import { defineConfig, loadEnv } from "vite"
import { VueMcp } from "vite-plugin-vue-mcp"
import svgLoader from "vite-svg-loader"

// Configuring Vite: https://cn.vite.dev/config
export default defineConfig(({ mode }) => {
  const { VITE_PUBLIC_PATH, VITE_PROXY_TARGET } = loadEnv(mode, process.cwd(), "") as ImportMetaEnv
  return {
    base: VITE_PUBLIC_PATH,
    resolve: {
      alias: {
        "@": resolve(__dirname, "src"),
        "@@": resolve(__dirname, "src/common")
      }
    },
    server: {
      host: true,
      port: 3333,
      strictPort: false,
      open: false,
      proxy: {
        "/api/admin": {
          target: VITE_PROXY_TARGET || "http://127.0.0.1:8000",
          ws: false,
          changeOrigin: true
        }
      },
      cors: true,
      warmup: {
        clientFiles: [
          "./src/layouts/**/*.*",
          "./src/pinia/**/*.*",
          "./src/router/**/*.*"
        ]
      }
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ["vue", "vue-router", "pinia"],
            element: ["element-plus", "@element-plus/icons-vue"],
            vxe: ["vxe-table"]
          }
        }
      },
      reportCompressedSize: false,
      chunkSizeWarningLimit: 2048
    },
    esbuild:
      mode === "development"
        ? undefined
        : {
            pure: ["console.log"],
            drop: ["debugger"],
            legalComments: "none"
          },
    optimizeDeps: {
      include: ["element-plus/es/components/*/style/css"]
    },
    css: {
      preprocessorMaxWorkers: true
    },
    plugins: [
      vue(),
      svgLoader({
        defaultImport: "url",
        svgoConfig: {
          plugins: [
            {
              name: "preset-default",
              params: {
                overrides: {
                  // @see https://github.com/svg/svgo/issues/1128
                  removeViewBox: false
                }
              }
            }
          ]
        }
      }),
      SvgComponent({
        iconDir: [resolve(__dirname, "src/common/assets/icons")],
        preserveColor: resolve(__dirname, "src/common/assets/icons/preserve-color"),
        dts: true,
        dtsDir: resolve(__dirname, "types/auto")
      }),
      UnoCSS(),
      AutoImport({
        imports: ["vue", "vue-router", "pinia"],
        dts: "types/auto/auto-imports.d.ts",
        resolvers: [ElementPlusResolver()]
      }),
      Components({
        dts: "types/auto/components.d.ts",
        resolvers: [ElementPlusResolver()]
      }),
      VueMcp()
    ],
    test: {
      include: ["tests/**/*.test.{ts,js}"],
      environment: "happy-dom",
      server: {
        deps: {
          inline: ["element-plus"]
        }
      }
    }
  }
})
