import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// NSosyal MÜHÜR — frontend dev sunucusu.
// Backend (FastAPI) 127.0.0.1:8000'de calisir; API adresi src/api.js icinde.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
})
