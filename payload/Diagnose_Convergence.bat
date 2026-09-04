@echo off
rem ===========================================================================
rem Diagnose_Convergence.bat - capture the REAL error from me3.
rem
rem Why this exists: Start_Convergence.bat cannot show you the failure. It sets
rem ME3_CONSOLE_LOG_LEVEL=error and then uses "start" to fire me3 off into a
rem separate window that closes the instant it exits. Everything me3 prints is
rem thrown away. The "Failed to launch / mod should not be installed in the
rem ELDEN RINGGame folder" text you see afterwards is the .bat's own guesswork,
rem not me3's error, and under Proton that guesswork is wrong anyway.
rem
rem This script runs the same launch in the FOREGROUND with full logging and
rem writes everything to me3-diagnostic.txt beside this file.
rem
rem Run it the same way you run Start_Convergence.bat (same Proton setup),
rem then send me3-diagnostic.txt.
rem
rem Deliberately written in simple syntax: Wine's cmd does not support
rem findstr /b or quoted substring substitution, which is what breaks the
rem original launcher's self-diagnosis.
rem ===========================================================================

cd /d "%~dp0"

set ME3_CONSOLE_LOG_LEVEL=trace
set ME3_FILE_LOG_LEVEL=trace
set OUT=%~dp0me3-diagnostic.txt

echo.
echo Collecting diagnostics. This will try to launch the game.
echo Output file: "%OUT%"
echo.

echo ======================= ENVIRONMENT ======================= > "%OUT%"
echo Working directory: %CD% >> "%OUT%"
echo LOCALAPPDATA: %LOCALAPPDATA% >> "%OUT%"
echo APPDATA: %APPDATA% >> "%OUT%"
echo USERPROFILE: %USERPROFILE% >> "%OUT%"
echo. >> "%OUT%"

echo ======================= FILE CHECKS ======================= >> "%OUT%"
if exist ".\me3\Windows\me3.exe" echo OK   me3\Windows\me3.exe >> "%OUT%"
if not exist ".\me3\Windows\me3.exe" echo MISSING   me3\Windows\me3.exe >> "%OUT%"
if exist ".\me3\Windows\me3-launcher.exe" echo OK   me3\Windows\me3-launcher.exe >> "%OUT%"
if not exist ".\me3\Windows\me3-launcher.exe" echo MISSING   me3\Windows\me3-launcher.exe >> "%OUT%"
if exist ".\me3\Windows\me3_mod_host.dll" echo OK   me3\Windows\me3_mod_host.dll >> "%OUT%"
if not exist ".\me3\Windows\me3_mod_host.dll" echo MISSING   me3\Windows\me3_mod_host.dll >> "%OUT%"
if exist ".\mod\regulation.bin" echo OK   mod\regulation.bin >> "%OUT%"
if not exist ".\mod\regulation.bin" echo MISSING   mod\regulation.bin >> "%OUT%"
echo. >> "%OUT%"

echo ======================= me3 --version ======================= >> "%OUT%"
".\me3\Windows\me3.exe" --version >> "%OUT%" 2>&1
echo exit code: %ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

echo ======================= me3 info ======================= >> "%OUT%"
echo (this prints me3's install and SEARCH PATHS - it is how me3 finds the game) >> "%OUT%"
".\me3\Windows\me3.exe" info >> "%OUT%" 2>&1
echo exit code: %ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

set PROFILE=.\me3\convergence.me3

echo ======================= PROFILE ======================= >> "%OUT%"
echo Using: %PROFILE% >> "%OUT%"
echo. >> "%OUT%"
type "%PROFILE%" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo ======================= LAUNCH ATTEMPT ======================= >> "%OUT%"
echo Running me3 in the foreground with trace logging. >> "%OUT%"
echo. >> "%OUT%"
".\me3\Windows\me3.exe" launch --auto-detect --diagnostics -p "%PROFILE%" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo me3 exit code: %ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

echo ======================= me3 LOG FILES ======================= >> "%OUT%"
if exist "%LOCALAPPDATA%\garyttierney\me3\data\logs" dir /s /b /o-d "%LOCALAPPDATA%\garyttierney\me3\data\logs" >> "%OUT%" 2>&1
if exist "%LOCALAPPDATA%\garyttierney\me3\data\logs" xcopy /s /y /i /q "%LOCALAPPDATA%\garyttierney\me3\data\logs" "%~dp0me3-logs-collected" >nul 2>&1
if exist "%~dp0me3-logs-collected" echo me3 detail logs copied to me3-logs-collected >> "%OUT%"
if exist "%LOCALAPPDATA%\me3\me3-logs" dir /b /o-d "%LOCALAPPDATA%\me3\me3-logs" >> "%OUT%" 2>&1
if exist "%LOCALAPPDATA%\me3-logs" dir /b /o-d "%LOCALAPPDATA%\me3-logs" >> "%OUT%" 2>&1
if exist "%APPDATA%\me3\me3-logs" dir /b /o-d "%APPDATA%\me3\me3-logs" >> "%OUT%" 2>&1
if exist "%USERPROFILE%\me3-logs" dir /b /o-d "%USERPROFILE%\me3-logs" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo (if none listed above, read the "me3 info" section for the real log path) >> "%OUT%"
echo. >> "%OUT%"

echo ======================= END ======================= >> "%OUT%"

cls
type "%OUT%"
echo.
echo ---------------------------------------------------------------
echo Saved to: "%OUT%"
echo Send that file. The LAUNCH ATTEMPT and me3 info sections
echo contain the actual reason the game did not start.
echo ---------------------------------------------------------------
pause
