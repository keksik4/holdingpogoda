@echo off
setlocal
cd /d "%~dp0"
echo.
echo Welcome to AIrlines - local preview
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
echo Starting Streamlit at http://localhost:8501
echo Keep the backend running in another window.
echo.
python -m streamlit run local_preview\app.py
pause
