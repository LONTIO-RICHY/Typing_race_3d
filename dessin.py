"""Outil de dessin : ajoute automatiquement un tag à chaque élément du canvas.

Le fond fixe (tag "static") n'est dessiné qu'une fois ; seul ce qui bouge
(tag "dyn") est effacé et redessiné à chaque image.

Le jeu est dessiné dans un repère fixe de W x H (900 x 560). Le Peintre le met
à l'échelle de la fenêtre : agrandir la fenêtre ou passer en plein écran
agrandit tout (formes, textes, épaisseurs) en gardant les proportions, avec
des bandes de la couleur du fond si l'écran n'a pas le même format.
"""

import math

from config import FOND, H, W


class Peintre:
    def __init__(self, canvas):
        self.c = canvas
        self.tag = "dyn"
        self.s = 1.0                 # échelle
        self.ox = self.oy = 0.0      # décalage (bandes autour du jeu)
        self.taille = (W, H)         # taille actuelle de la fenêtre en pixels

    def regler(self, largeur, hauteur):
        """Appelé quand la fenêtre change de taille."""
        largeur, hauteur = max(1, int(largeur)), max(1, int(hauteur))
        self.s = min(largeur / W, hauteur / H)
        self.ox = (largeur - W * self.s) / 2
        self.oy = (hauteur - H * self.s) / 2
        self.taille = (largeur, hauteur)

    def vers_jeu(self, ex, ey):
        """Position de la souris (pixels de la fenêtre) -> repère du jeu (900 x 560)."""
        return ((ex - self.ox) / self.s, (ey - self.oy) / self.s)

    # ---------------------------------------------------------------- échelle
    def _xy(self, coords):
        """Liste plate x, y, x, y... -> coordonnées écran."""
        if self.s == 1.0 and not self.ox and not self.oy:
            return coords
        s, ox, oy = self.s, self.ox, self.oy
        sortie = list(coords)
        sortie[0::2] = [ox + x * s for x in coords[0::2]]
        sortie[1::2] = [oy + y * s for y in coords[1::2]]
        return sortie

    def _kw(self, kw, texte=False):
        """Met à l'échelle la police et les épaisseurs (ou la largeur de retour à la ligne d'un texte)."""
        s = self.s
        if s != 1.0:
            if "width" in kw:
                w = kw["width"] * s
                kw["width"] = w if texte else max(1, round(w))
            f = kw.get("font")
            if f:
                kw["font"] = (f[0], max(6, round(f[1] * s))) + tuple(f[2:])
        return kw

    # ---------------------------------------------------------------- formes
    def rect(self, x0, y0, x1, y1, r=0, **kw):
        if r:                                   # r = rayon des coins arrondis
            return self.rrect(x0, y0, x1, y1, r, **kw)
        kw.setdefault("outline", "")
        return self.c.create_rectangle(*self._xy((x0, y0, x1, y1)), tags=self.tag, **self._kw(kw))

    def rrect(self, x0, y0, x1, y1, r=10, **kw):
        """Rectangle aux coins arrondis (polygone dont les coins sont de vrais quarts de cercle)."""
        r = min(r, abs(x1 - x0) / 2, abs(y1 - y0) / 2)
        if r < 1:
            return self.rect(x0, y0, x1, y1, **kw)
        n = 5 if r < 14 else 7                       # segments par coin
        pts = []
        for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
            for k in range(n + 1):
                a = math.radians(a0 + 90 * k / n)
                pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
        kw.setdefault("outline", "")
        kw.setdefault("fill", "")
        return self.c.create_polygon(self._xy(pts), tags=self.tag, **self._kw(kw))

    def oval(self, x0, y0, x1, y1, **kw):
        kw.setdefault("outline", "")
        return self.c.create_oval(*self._xy((x0, y0, x1, y1)), tags=self.tag, **self._kw(kw))

    def poly(self, pts, **kw):
        kw.setdefault("outline", "")
        return self.c.create_polygon(self._xy(pts), tags=self.tag, **self._kw(kw))

    def ligne(self, *coords, **kw):
        return self.c.create_line(*self._xy(coords), tags=self.tag, **self._kw(kw))

    def texte(self, x, y, **kw):
        return self.c.create_text(*self._xy((x, y)), tags=self.tag, **self._kw(kw, texte=True))

    def arc(self, x0, y0, x1, y1, **kw):
        return self.c.create_arc(*self._xy((x0, y0, x1, y1)), tags=self.tag, **self._kw(kw))

    def masque(self):
        """Cache ce qui dépasse du jeu sur les bandes (à appeler en dernier, à chaque image)."""
        if self.ox < 0.5 and self.oy < 0.5:
            return
        w, h = self.taille
        ox, oy = int(self.ox) + 1, int(self.oy) + 1
        for x0, y0, x1, y1 in ((0, 0, ox, h), (w - ox, 0, w, h), (0, 0, w, oy), (0, h - oy, w, h)):
            if x1 > x0 and y1 > y0:
                self.c.create_rectangle(x0, y0, x1, y1, fill=FOND, outline="", tags=self.tag)
