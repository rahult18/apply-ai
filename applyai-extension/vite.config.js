import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { copyFileSync, mkdirSync, existsSync } from 'fs';

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
