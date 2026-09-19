import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/clarify': 'http://localhost:8000',
      '/research': 'http://localhost:8000',
      '/reports': 'http://localhost:8000',
    },
  },
})
