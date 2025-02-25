@echo off
title SageExtract - The Monolithic Sage 100 Data Extractor
color 0B

echo.
echo  ^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*
echo  ^*                                                                ^*
echo  ^*                    SageExtract v1.0                            ^*
echo  ^*                                                                ^*
echo  ^*     "All the power, none of the clutter."                      ^*
echo  ^*          - Malloc, Raven of Forbidden Functions                ^*
echo  ^*                                                                ^*
echo  ^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*
echo.

echo Preparing to extract data from the ancient Sage 100 scrolls...
echo.

REM Check if Python is installed
python --version > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed or not in your PATH.
    echo Please install Python 3.x from https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check if pyodbc is installed
python -c "import pyodbc" > nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Installing required dependency: pyodbc...
    pip install pyodbc
    if %ERRORLEVEL% neq 0 (
        echo Failed to install pyodbc. Please run as administrator or install manually:
        echo pip install pyodbc
        pause
        exit /b 1
    )
)

REM Get the full path to the database
for %%I in ("%~dp0") do set "SCRIPT_DIR=%%~fI"
set "DB_PATH=%SCRIPT_DIR%db\sage_data.db"

echo Dependencies verified. Beginning extraction ritual...
echo.
echo WARNING: This will DROP all existing tables in the database to prevent duplicates.
echo Database location: %DB_PATH%
echo.
echo Press Ctrl+C now to cancel, or...
pause
echo.
echo Summoning data from Sage 100 (this may take several minutes)...
echo.

REM Run the extraction script
python extract_data.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: An error occurred during extraction. See above for details.
    echo.
    pause
    exit /b 1
)

echo.
echo ^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*
echo ^*                                                                ^*
echo ^*                   EXTRACTION COMPLETE!                         ^*
echo ^*                                                                ^*
echo ^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*^*
echo.

echo Your data has been successfully extracted to:
echo %DB_PATH%
echo.
echo To connect using DBeaver:
echo  1. Open DBeaver
echo  2. Click "New Database Connection" (database+ icon)
echo  3. Select "SQLite"
echo  4. In the "Path" field, enter: %DB_PATH%
echo  5. Click "Test Connection" to verify
echo  6. Click "Finish" to create the connection
echo.
echo You can now query your data using SQL!
echo.

pause 