@echo off
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building FractalSaver.exe...
pyinstaller --onefile --noconsole ^
    --name FractalSaver ^
    --add-data "fractals;fractals" ^
    main.py

echo.
echo Renaming to .scr...
ren dist\FractalSaver.exe FractalSaver.scr

echo.
echo =====================================================
echo  Done!
echo.
echo  To install as a screensaver:
echo    copy dist\FractalSaver.scr C:\Windows\System32\
echo.
echo  Then go to:
echo    Settings > Personalization > Lock screen > Screen saver
echo    and select "FractalSaver"
echo =====================================================
pause
