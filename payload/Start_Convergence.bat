@echo off
rem ===========================================================================
rem The Convergence: Elden Ring  -  launcher (Elden Ring 1.17 build)
rem
rem Works on Windows, and on Linux / Steam Deck when run through Proton.
rem It tells the mod loader (me3) exactly where eldenring.exe is, so it does
rem not depend on Steam being visible from inside a Proton prefix.
rem
rem How the game is found, in order:
rem   1. GAME_EXE below, if you set it (any copy of the game, Steam or not);
rem   2. ..\Game\eldenring.exe next to this folder (the recommended layout:
rem        ...\ELDEN RING\Game\eldenring.exe
rem        ...\ELDEN RING\ConvergenceER\Start_Convergence.bat   <- this file);
rem   3. otherwise me3 asks Steam where Elden Ring is installed (normal Steam
rem      install placed anywhere; this is how the original mod launched).
rem
rem To point at a specific eldenring.exe, set the full path here:
set GAME_EXE=
rem   e.g.  set GAME_EXE=D:\Games\ELDEN RING\Game\eldenring.exe
rem
rem Keep this window open while you play. me3's output is saved to
rem me3-launch.log next to this file; if the game does not start, run
rem Diagnose_Convergence.bat and read that log.
rem ===========================================================================

chcp 65001 > nul
cd /d "%~dp0"

set ME3_CONSOLE_LOG_LEVEL=info
set ME3_FILE_LOG_LEVEL=debug
set LOG=%~dp0me3-launch.log

taskkill /im eldenring.exe /f >nul 2>&1

if not "%GAME_EXE%"=="" goto have_game
if exist "%~dp0..\Game\eldenring.exe" set GAME_EXE=%~dp0..\Game\eldenring.exe
if not "%GAME_EXE%"=="" goto have_game
if exist "%~dp0..\ELDEN RING\Game\eldenring.exe" set GAME_EXE=%~dp0..\ELDEN RING\Game\eldenring.exe
if not "%GAME_EXE%"=="" goto have_game

rem Not found next to this folder: fall back to letting me3 find the game through Steam
rem (works for a normal Steam install placed anywhere; Steam must be running).
set PROFILE=.\me3\convergence.me3
echo The Convergence: Elden Ring  (Elden Ring 1.17 build)
echo Game:  located through Steam (set GAME_EXE in this file to use a specific eldenring.exe)
echo Log:   "%LOG%"
echo.
echo Launching. Keep this window open while you play.
echo.
".\me3\Windows\me3.exe" launch --auto-detect -p "%PROFILE%" > "%LOG%" 2>&1
if errorlevel 1 goto failed
exit /b 0

:have_game
set PROFILE=.\me3\convergence.me3
echo The Convergence: Elden Ring  (Elden Ring 1.17 build)
echo Game:  "%GAME_EXE%"
echo Log:   "%LOG%"
echo.
echo Launching. Keep this window open while you play.
echo.

".\me3\Windows\me3.exe" launch --auto-detect --exe "%GAME_EXE%" -p "%PROFILE%" > "%LOG%" 2>&1

if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo ============================================================
echo me3 reported an error. Its output follows and is saved to:
echo "%LOG%"
echo ============================================================
echo.
type "%LOG%"
echo.
echo ------------------------------------------------------------
echo Common causes:
echo  - Steam is not running (needed for a Steam copy of the game).
echo  - GAME_EXE points at the wrong copy of the game, or the game was not
echo    found next to this folder and Steam could not locate it: set GAME_EXE.
echo  - The game is not on patch 1.17 (this build needs 1.17).
echo  - A DLL failed to load; the log names it.
echo ------------------------------------------------------------
echo.
pause
exit /b 1
