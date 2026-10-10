"""Particules : étincelles, fumée d'échappement, confettis."""

import random

from config import H, W
from moteur3d import melanger

COULEURS_CONFETTIS = ["#ef4444", "#facc15", "#4ade80", "#4cc9f0", "#c084fc", "#fb923c"]


class Particules:
    def __init__(self):
        self.liste = []

    def vider(self):
        self.liste = []

    def _ajouter(self, **q):
        if len(self.liste) < 300:
            self.liste.append(q)

    def etincelles(self, x, y):
        for _ in range(12):
            self._ajouter(type="etincelle", x=x, y=y,
                          vx=random.uniform(-130, 130), vy=random.uniform(-190, -30),
                          vie=0.5, vie_max=0.5, taille=3,
                          couleur=random.choice(["#fbbf24", "#f97316", "#fde047"]))

    def fumee(self, x, y):
        self._ajouter(type="fumee", x=x, y=y,
                      vx=random.uniform(-25, 25), vy=random.uniform(-45, -12),
                      vie=0.7, vie_max=0.7, taille=3, couleur="#d1d5db")

    def confettis(self):
        for _ in range(120):
            self._ajouter(type="confetti", x=random.uniform(0, W),
                          y=random.uniform(-250, 0),
                          vx=random.uniform(-30, 30), vy=random.uniform(100, 220),
                          vie=5, vie_max=5, taille=random.randint(5, 9),
                          couleur=random.choice(COULEURS_CONFETTIS))

    def maj(self, dt):
        for q in self.liste:
            q["vie"] -= dt
            q["x"] += q["vx"] * dt
            q["y"] += q["vy"] * dt
            if q["type"] == "etincelle":
                q["vy"] += 500 * dt
            elif q["type"] == "confetti":
                q["vx"] += random.uniform(-60, 60) * dt
        self.liste = [q for q in self.liste if q["vie"] > 0 and q["y"] < H + 20]

    def dessiner(self, p):
        for q in self.liste:
            x, y, r = q["x"], q["y"], q["taille"]
            if q["type"] == "fumee":
                g = r + (1 - q["vie"] / q["vie_max"]) * 8
                # la fumée s'efface en se fondant dans la route (couleur unie : plus rapide que le stipple)
                p.oval(x - g, y - g, x + g, y + g,
                       fill=melanger(q["couleur"], "#5a5e65", 1 - q["vie"] / q["vie_max"]))
            elif q["type"] == "confetti":
                p.rect(x, y, x + r, y + r * 0.6, fill=q["couleur"])
            else:
                p.oval(x - r / 2, y - r / 2, x + r / 2, y + r / 2, fill=q["couleur"])
