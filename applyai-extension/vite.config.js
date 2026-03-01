import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { copyFileSync, mkdirSync, existsSync, readdirSync, writeFileSync, readFileSync } from 'fs';

export default defineConfig(({ mode }) => {
  // Load .env.development or .env.production based on the build mode.
  // The third argument '' means load all vars (not just VITE_ prefixed).
  const env = loadEnv(mode, process.cwd(), '');

  const APP_BASE_URL = env.VITE_APP_BASE_URL || 'http://localhost:3000';
  const API_BASE_URL = env.VITE_API_BASE_URL || 'http://localhost:8000';

  return {
    plugins: [
      react(),
      {
        name: 'copy-extension-files',
        writeBundle() {
          // Ensure dist directory exists
          if (!existsSync('dist')) {
            mkdirSync('dist', { recursive: true });
          }

          // Copy content.js (not processed by Vite — no env vars needed)
          copyFileSync('content.js', 'dist/content.js');

          // Copy assets folder
          if (existsSync('assets')) {
            if (!existsSync('dist/assets')) {
              mkdirSync('dist/assets', { recursive: true });
            }
            const assetFiles = readdirSync('assets');
            assetFiles.forEach(file => {
              copyFileSync(`assets/${file}`, `dist/assets/${file}`);
            });
          }

          // Generate manifest.json with environment-specific URLs injected.
          // This replaces the static manifest.json copy so content_scripts and
          // host_permissions always match the active build environment.
          const manifest = JSON.parse(readFileSync('manifest.json', 'utf-8'));

          manifest.content_scripts[0].matches = [
            `${APP_BASE_URL}/extension/connect*`
          ];

          manifest.host_permissions = [
            `${APP_BASE_URL}/*`,
            `${API_BASE_URL}/*`
          ];

          // Required for the service worker to use ES module imports
          // (background.js now imports from shared/config.js via Vite bundling)
          manifest.background.type = 'module';

          writeFileSync('dist/manifest.json', JSON.stringify(manifest, null, 2));
        }
      }
    ],
    build: {
      outDir: 'dist',
      rollupOptions: {
        input: {
          // Popup React app entry
          popup: resolve(__dirname, 'popup/index.html'),
          // Service worker — bundled by Vite so import.meta.env is replaced.
          // background.js was previously copied as-is; now it's a proper entry point.
          background: resolve(__dirname, 'background.js'),
        },
        output: {
          entryFileNames: '[name].js',
          chunkFileNames: '[name].js',
          assetFileNames: '[name].[ext]'
        }
      }
    }
  };
});
