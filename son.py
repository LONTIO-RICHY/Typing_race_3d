"""Sons générés par le programme (Windows uniquement, sans fichier à installer)."""

import math
import struct
import tempfile
import wave
from pathlib import Path

try:
    import winsound
except ImportError:          # Linux, Mac, Android : le jeu reste muet
    winsound = None

RATE = 22050
DOSSIER = Path(tempfile.gettempdir()) / "typing_race_sons"


def _ecrire_wav(nom, segments, volume=0.3, forme="sinus"):
    """segments : liste de (fréquence_Hz, durée_s). Retourne le chemin du .wav"""
    DOSSIER.mkdir(exist_ok=True)
    chemin = DOSSIER / f"{nom}.wav"
    frames = bytearray()
    for freq, duree in segments:
        n = int(RATE * duree)
        for i in range(n):
            if freq:
                phase = math.sin(2 * math.pi * freq * i / RATE)
                v = phase if forme == "sinus" else (1.0 if phase >= 0 else -1.0)
                env = min(1.0, i / (RATE * 0.004), (n - i) / (RATE * 0.01))
                v *= env
            else:
                v = 0.0
            frames += struct.pack("<h", int(v * volume * 32767))
    with wave.open(str(chemin), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))
    return str(chemin)


class Son:
    def __init__(self, muet=False):
        self.muet = muet
        self.actif = winsound is not None
        if not self.actif:
            return
        try:
            # le "clic" monte en hauteur quand tu tapes plus vite (effet moteur)
            self.clics = [_ecrire_wav(f"clic{i}", [(200 + i * 70, 0.03)], 0.25)
                          for i in range(8)]
            self.s_erreur = _ecrire_wav("erreur", [(110, 0.12)], 0.35, "carre")
            self.s_bip = _ecrire_wav("bip", [(660, 0.12)], 0.35)
            self.s_depart = _ecrire_wav("depart", [(990, 0.35)], 0.35)
            self.s_victoire = _ecrire_wav(
                "victoire", [(523, .12), (659, .12), (784, .12), (1047, .3)], 0.35)
            self.s_defaite = _ecrire_wav(
                "defaite", [(392, .2), (330, .2), (262, .35)], 0.35)
        except OSError:
            self.actif = False

    def _jouer(self, chemin):
        if self.muet or not self.actif:
            return
        try:
            winsound.PlaySound(chemin, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    def clic(self, wpm):
        if self.actif:
            self._jouer(self.clics[max(0, min(7, int(wpm // 20)))])

    def erreur(self):
        if self.actif:
            self._jouer(self.s_erreur)

    def bip(self):
        if self.actif:
            self._jouer(self.s_bip)

    def depart(self):
        if self.actif:
            self._jouer(self.s_depart)

    def victoire(self):
        if self.actif:
            self._jouer(self.s_victoire)

    def defaite(self):
        if self.actif:
            self._jouer(self.s_defaite)
