@echo off
setlocal
cd /d "%~dp0frontend"

if not exist ".env.local" (
  copy ".env.example" ".env.local" >nul
)

if not exist "node_modules" (
  echo Installing frontend packages. This can take a few minutes on first run...
  call npm.cmd install
  if errorlevel 1 (
    echo.
    echo Package installation failed. Check your internet connection and rerun this file.
    pause
    exit /b 1
  )
)

echo.
echo Starting Pogoda w Lodzi frontend at http://localhost:3000
echo Backend API expected at %NEXT_PUBLIC_API_BASE_URL%
echo.
call npm.cmd run dev

endlocal
