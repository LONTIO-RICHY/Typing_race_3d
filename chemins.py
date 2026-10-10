"""Où le jeu range ses fichiers (sauvegarde, musiques, journal d'erreurs).

En développement (python main.py) : à côté des fichiers .py.
Une fois transformé en .exe avec PyInstaller : à côté du .exe. Il ne faut surtout
pas utiliser le dossier du code, car avec « --onefile » il est temporaire et
supprimé à chaque fermeture (la progression serait perdue).
Si le dossier du .exe est protégé en écriture (ex. Program Files), on utilise
%APPDATA%\\TypingRace3D à la place.
"""

import os
import sys
import tempfile
from pathlib import Path


def en_exe():
    """Vrai quand le jeu tourne depuis un .exe PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def _ecriture_possible(dossier):
    try:
        dossier.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=dossier):
            pass
        return True
    except OSError:
        return False


def dossier_donnees():
    if not en_exe():
        return Path(__file__).resolve().parent
    base = Path(sys.executable).resolve().parent
    if _ecriture_possible(base):
        return base
    appdata = os.environ.get("APPDATA")
    secours = (Path(appdata) if appdata else Path.home()) / "TypingRace3D"
    secours.mkdir(parents=True, exist_ok=True)
    return secours


def chemin_ressource(nom):
    """Fichier livré avec le jeu (ex. l'icône). Dans le .exe : dossier de PyInstaller (--add-data)."""
    if en_exe():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / nom
    return Path(__file__).resolve().parent / nom
