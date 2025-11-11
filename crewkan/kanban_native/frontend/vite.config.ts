import { defineConfig } from 'vite';

export default defineConfig({
  base: './',  // Use relative paths for assets
  build: {
    outDir: 'build',
    rollupOptions: {
      input: 'src/index.tsx',  // Direct entry point instead of HTML
      output: {
        entryFileNames: 'index.js',
        format: 'iife',  // Use IIFE instead of ES modules to avoid MIME type issues
        name: 'KanbanBoard',
        inlineDynamicImports: true
      }
    }
  },
  server: {
    port: 3001,
    strictPort: true,
    host: '0.0.0.0'  // Allow access from remote connections
  }
});

