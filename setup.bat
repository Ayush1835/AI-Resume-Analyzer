@echo off
echo ===================================================
echo   AI Resume Analyzer - Quick Setup and Startup
echo ===================================================
echo.

:: Check python version
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your system PATH.
    echo Please install Python 3.12+ and try again.
    pause
    exit /b 1
)

:: Step 1: Create Virtual Environment
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [*] Virtual environment already exists. Skipping creation.
)

:: Step 2: Install dependencies
echo [2/4] Upgrading pip and installing requirements...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r backend/requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: Step 3: Download NLP models
echo [3/4] Downloading spaCy English model (en_core_web_sm)...
venv\Scripts\python.exe -m spacy download en_core_web_sm
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download spaCy model.
    pause
    exit /b 1
)

:: Step 4: Run verification tests
echo [4/4] Executing unit tests...
venv\Scripts\python.exe -m pytest backend/tests
if %errorlevel% neq 0 (
    echo [WARNING] Some tests failed. Please review tests logs.
) else (
    echo [SUCCESS] All unit tests passed!
)

echo.
echo ===================================================
echo   Setup Complete! Starting FastAPI Dev Server...
echo   Navigate to http://127.0.0.1:8000 in your browser.
echo   Press Ctrl+C inside this window to stop the server.
echo ===================================================
echo.

:: Launch Server from root package namespace
venv\Scripts\python.exe main.py
pause
