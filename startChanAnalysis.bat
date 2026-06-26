@echo off
setlocal

cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

python -m streamlit run web_app/app.py

if errorlevel 1 (
    echo Failed to start web app. Please run:
    echo python -m streamlit run web_app/app.py
    goto :END
)

echo.
echo Script finished. Press any key to exit.
pause >nul

:END
endlocal
