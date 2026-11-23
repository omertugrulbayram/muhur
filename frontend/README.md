# NSosyal MÜHÜR — Frontend (React + Vite + Tailwind)

Güven ve otantiklik katmanının canlı arayüzü. Backend'e (FastAPI) bağlı çalışır.

## Çalıştırma
1. Önce backend'i başlat (ayrı terminal, `backend/` klasöründe):
   ```
   uvicorn app.main:app --reload
   ```
   (Backend main.py'de CORS açık olmalı — bu repoda ekli.)
2. Frontend (bu klasörde):
   ```
   npm install
   npm run dev
   ```
   Tarayıcı: http://localhost:5173

## Yapı
- `src/api.js`  — backend API istemcisi (adres: 127.0.0.1:8000)
- `src/App.jsx` — tüm arayüz: Mührünü Al akışı + Akış (Neden bunu görüyorum?)
- `src/index.css` — tasarım jetonları + mühür animasyonu (Tailwind v4 @theme)

Not: mock issuer / SİMÜLASYON. Skorlar canlı backend'den gelir.
