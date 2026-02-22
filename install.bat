@echo off
echo ================================================================================
echo EL PAIS OPINION SCRAPER - INSTALLATION SCRIPT
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/4] Python detected
python --version
echo.

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo [2/4] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
) else (
    echo [2/4] Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
echo.

REM Install dependencies
echo [4/4] Installing dependencies from requirements.txt...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo ================================================================================
echo INSTALLATION COMPLETED SUCCESSFULLY
echo ================================================================================
echo.
echo Next steps:
echo   1. Update .env.browserstack with your credentials
echo   2. Run locally: python opinion_scraper.py
echo   3. Run BrowserStack: python opinion_scraper_browserstack.py
echo   4. Run full test suite: python run_tests.py
echo.
echo To activate the virtual environment manually, run:
echo   .venv\Scripts\activate.bat
echo.
pause
