import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { copyFileSync, mkdirSync, existsSync, readdirSync } from 'fs';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'copy-extension-files',
      writeBundle() {
        // Ensure dist directory exists
        if (!existsSync('dist')) {
          mkdirSync('dist', { recursive: true });
        }

        // Copy manifest.json
        copyFileSync('manifest.json', 'dist/manifest.json');

        // Copy background.js
        copyFileSync('background.js', 'dist/background.js');

        // Copy content.js
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
      }
    }
  ],
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'popup/index.html')
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: '[name].js',
        assetFileNames: '[name].[ext]'
      }
    }
  }
});
