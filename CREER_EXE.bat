@echo off
cd /d "%~dp0"
echo === Creation de TypingRace3D.exe ===
python -c "import pygame" >nul 2>&1
if errorlevel 1 python -m pip install pygame
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 python -m pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --icon icone_typing_race.ico --add-data "icone_typing_race.ico;." --name TypingRace3D main.py
echo.
if exist dist\TypingRace3D.exe (
    echo Termine : dist\TypingRace3D.exe
    echo Copie ce fichier ou tu veux : la sauvegarde, le dossier sons et erreurs.log seront crees a cote de lui.
) else (
    echo La creation a echoue : lis les messages ci-dessus.
)
pause
