"""Musiques de course : le joueur les choisit avant de lancer la partie.

Crée un dossier "sons" à côté de main.py et mets-y tes fichiers en les
renommant avec des numéros :  1.mp3  2.mp3  3.wav  ...
(formats : .mp3 .ogg .wav .flac). Il faut pygame :  pip install pygame

Dans le jeu, chaque son se joue en boucle, et une entrée spéciale joue
tous les sons à la suite, en boucle (playlist).
"""

import os
import warnings
from pathlib import Path

from chemins import dossier_donnees

# pygame : pas de message de bienvenue ni d'avertissement pkg_resources dans le terminal
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
warnings.filterwarnings("ignore", message=".*pkg_resources.*", category=UserWarning)

try:
    import pygame
except ImportError:
    pygame = None

EXTENSIONS = {".mp3", ".ogg", ".wav", ".flac"}
PLAYLIST = "*playlist*"       # valeur sauvegardée pour "tous les sons en boucle"


class Musique:
    def __init__(self):
        self.dossier = dossier_donnees() / "sons"      # à côté du .exe : tu peux y déposer tes musiques
        try:
            premiere_fois = not self.dossier.exists()
            self.dossier.mkdir(parents=True, exist_ok=True)
            if premiere_fois:               # version .exe : le dossier sons n'existe pas encore, on explique comment l'utiliser
                (self.dossier / "LISEZ-MOI.txt").write_text(
                    "Mets tes musiques dans CE dossier (.mp3 .ogg .wav .flac) et numerote-les :\n"
                    "1.mp3  2.mp3  3.mp3 ...  Relance le jeu, puis choisis la musique dans le menu.\n",
                    encoding="utf-8")
        except OSError:
            pass
        self.actif = False
        self.erreur = ""
        if pygame is None:
            self.erreur = "pygame manquant : pip install pygame"
        else:
            try:
                pygame.mixer.init()
                self.actif = True
            except Exception:
                self.erreur = "audio indisponible sur cet appareil"
        self.pistes = self.scanner()
        self.volume = 0.6
        self.muet = False
        self.playlist = False
        self.i_playlist = 0

    # ---------------------------------------------------------------- fichiers
    def scanner(self):
        """Fichiers triés : 1, 2, 3 ... 10 (ordre numérique), puis les autres noms."""
        try:
            fichiers = [f for f in self.dossier.iterdir()
                        if f.is_file() and f.suffix.lower() in EXTENSIONS]
        except OSError:
            return []

        def cle(f):
            return (0, int(f.stem), "") if f.stem.isdigit() else (1, 0, f.name.lower())

        return sorted(fichiers, key=cle)

    @staticmethod
    def titre(fichier):
        return f"Son {int(fichier.stem)}" if fichier.stem.isdigit() else fichier.stem

    # ---------------------------------------------------------------- lecture
    def regler_volume(self, volume, muet=False):
        self.volume, self.muet = volume, muet
        if self.actif:
            try:
                pygame.mixer.music.set_volume(0 if muet else volume)
            except Exception:
                pass

    def _lire(self, chemin, boucles):
        if not self.actif:
            return
        try:
            pygame.mixer.music.load(str(chemin))
            pygame.mixer.music.set_volume(0 if self.muet else self.volume)
            pygame.mixer.music.play(boucles)
        except Exception:
            pass

    def jouer(self, nom):
        """Joue un seul son en boucle (nom = nom de fichier), ou la playlist."""
        self.playlist = False
        if nom == PLAYLIST:
            self.jouer_playlist()
            return
        chemin = self.dossier / nom
        if nom and chemin.exists():
            self._lire(chemin, -1)          # -1 = boucle infinie

    def jouer_playlist(self):
        """Joue tous les sons à la suite, puis recommence au premier."""
        if not self.pistes:
            return
        self.playlist = True
        self.i_playlist = 0
        self._lire(self.pistes[0], 0)

    def maj(self):
        """À appeler régulièrement : passe au son suivant en mode playlist."""
        if not (self.playlist and self.actif and self.pistes):
            return
        try:
            if not pygame.mixer.music.get_busy():
                self.i_playlist = (self.i_playlist + 1) % len(self.pistes)
                self._lire(self.pistes[self.i_playlist], 0)
        except Exception:
            pass

    def arreter(self, fondu_ms=0):
        self.playlist = False
        if not self.actif:
            return
        try:
            if fondu_ms:
                pygame.mixer.music.fadeout(fondu_ms)
            else:
                pygame.mixer.music.stop()
        except Exception:
            pass
