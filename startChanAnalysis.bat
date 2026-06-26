@echo off
setlocal

cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PATH=%USERPROFILE%\.cargo\bin;%PATH%"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

if not exist "czsc\_native.pyd" (
    echo Native extension czsc\_native.pyd was not found.
    echo Building local Rust extension. This can take several minutes on the first run...
    python -m maturin develop --skip-install
    if errorlevel 1 (
        echo Failed to build czsc native extension.
        echo Please make sure Rust and maturin are installed, then run:
        echo python -m pip install maturin
        echo python -m maturin develop --skip-install
        goto :END
    )
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
