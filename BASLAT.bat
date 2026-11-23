@echo off
title NSosyal MUHUR
cd /d "%~dp0"
echo.
echo   NSosyal MUHUR (SEAL) - demo sunucusu
echo   ------------------------------------
if not exist "backend\.venv\Scripts\python.exe" (
  echo   [1/3] Python ortami kuruluyor ^(ilk sefer, birkac dakika^)...
  python -m venv backend\.venv || goto :hata
  backend\.venv\Scripts\python -m pip install -q -r backend\requirements.txt || goto :hata
) else (
  echo   [1/3] Python ortami hazir.
)
where npm >nul 2>nul
if %errorlevel%==0 (
  pushd frontend
  if not exist node_modules (
    echo   [2/3] Arayuz paketleri kuruluyor...
    call npm install --silent || goto :hata
  )
  echo   [2/3] Arayuz derleniyor...
  call npm run build --silent >nul || goto :hata
  popd
) else (
  if not exist "frontend\dist\index.html" (
    echo   Node.js bulunamadi ve derlenmis arayuz yok. https://nodejs.org adresinden kurun.
    goto :hata
  )
  echo   [2/3] Node.js yok, hazir derlenmis arayuz kullaniliyor.
)
echo   [3/3] Sunucu basliyor: http://127.0.0.1:8000
echo   Kapatmak icin bu pencerede Ctrl+C.
echo.
start "" cmd /c "timeout /t 5 >nul & start http://127.0.0.1:8000/"
cd backend
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
goto :eof
:hata
echo.
echo   Bir hata oldu. Yukaridaki mesaja bakin.
pause
