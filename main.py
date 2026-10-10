"""Lance le jeu : python main.py   (ou le .exe créé avec CREER_EXE.bat)"""

import os
import warnings

# Avant l'import de pygame (musique) : terminal propre, sans message de bienvenue ni avertissement.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings("ignore", message=".*pkg_resources.*", category=UserWarning)

import tkinter as tk

from jeu import Jeu

if __name__ == "__main__":
    racine = tk.Tk()
    Jeu(racine)
    racine.mainloop()
