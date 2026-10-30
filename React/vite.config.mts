import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        proxy: {
            // Keep the browser host so Django sees the same origin for CSRF checks.
            '/api/': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000', changeOrigin: false },
        },
    },
    build: {
        outDir: 'build',
        rolldownOptions: {
            output: {
                codeSplitting: {
                    groups: [
                        // Cache the shared React runtime separately from application code.
                        { name: 'react-runtime', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
                    ],
                },
            },
        },
    },
});

