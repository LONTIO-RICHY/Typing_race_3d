@echo off
cd /d "%~dp0"
python -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo Installation de pygame pour la musique...
    python -m pip install pygame
)
python main.py
pause
