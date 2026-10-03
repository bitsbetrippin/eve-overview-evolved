@echo off
setlocal DisableDelayedExpansion
title Eve-Overlay-Evolved v0.7.6
pushd "%~dp0"
if errorlevel 1 goto folder_error
if not exist "runtime\python.exe" goto missing_runtime
if not exist "startup.py" goto missing_files
echo Starting Eve-Overlay-Evolved v0.7.6...
"runtime\python.exe" -I -B "startup.py" %*
set "result=%errorlevel%"
if "%result%"=="0" goto done
echo.
echo Startup failed. See the error above and startup.log in this folder.
pause
:done
popd
exit /b %result%
:missing_runtime
echo The bundled Python runtime is missing.
echo Extract the complete Eve-Overlay-Evolved-v0.7.6-Windows-x64.zip release.
goto failed
:missing_files
echo Application files are missing. Extract the complete ZIP and try again.
:failed
pause
popd
exit /b 1
:folder_error
echo Could not open the application folder. Extract the ZIP to a writable folder.
pause
exit /b 1
