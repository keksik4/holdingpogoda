@echo off
setlocal
cd /d "%~dp0"
echo.
echo Pogoda w Lodzi - backend
echo.
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env from .env.example
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating local Python environment...
  py -3 -m venv .venv
  if errorlevel 1 (
    python -m venv .venv
    if errorlevel 1 (
      echo Could not create virtual environment. Install Python 3.11 or newer from https://www.python.org/downloads/windows/
      pause
      exit /b 1
    )
  )
)
call ".venv\Scripts\activate.bat"
set PYTHONPATH=%CD%
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Starting FastAPI at http://127.0.0.1:8000
echo API docs: http://127.0.0.1:8000/docs
echo.
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
pause
