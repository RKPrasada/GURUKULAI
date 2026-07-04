@echo off
:: Build VidyaBot Windows .exe installer
echo ==============================
echo   VidyaBot Windows Builder
echo ==============================

cd /d "%~dp0\.."
set ROOT=%CD%

echo Installing dependencies...
pip install -r requirements.txt pyinstaller

echo Running PyInstaller...
pyinstaller packaging\vidyabot.spec --distpath packaging\dist\windows --workpath packaging\build

echo Creating ZIP archive...
cd packaging\dist\windows
powershell -Command "Compress-Archive -Path VidyaBot -DestinationPath ..\VidyaBot-Windows-x64.zip -Force"
cd %ROOT%

echo.
echo Build complete!
echo   Archive: packaging\dist\VidyaBot-Windows-x64.zip
echo   Run: Extract ZIP and run VidyaBot\VidyaBot.exe
pause
