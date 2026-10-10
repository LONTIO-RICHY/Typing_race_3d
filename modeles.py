"""Modèles 3D : voitures et décor (arbres, immeubles, cactus, lampadaires...).

Repère : x = droite, y = haut, z = devant. Les voitures roulent vers +z,
leur arrière est donc du côté z négatif (c'est ce que voit la caméra).
"""

import random

from moteur3d import Maillage, anneaux, boite, cylindre_x, tronc

_cache = {}


def _roues(m, xs, zs, rayon, larg):
    for x in xs:
        for z in zs:
            cylindre_x(m, x, rayon, z, rayon, larg, 8, "pneu", "jante")


def _citadine(m):
    C = "carro"
    tronc(m, (-0.92, 0.92, -2.0, 2.0), 0.28, (-0.88, 0.88, -1.95, 1.95), 0.88, C)
    boite(m, -0.8, 0.8, 0.1, 0.3, -1.9, 1.9, "plastique", 1.5)
    tronc(m, (-0.86, 0.86, 0.9, 1.95), 0.88, (-0.82, 0.82, 1.0, 1.9), 0.96, C)        # capot
    tronc(m, (-0.82, 0.82, -1.2, 0.95), 0.88, (-0.7, 0.7, -0.85, 0.45), 1.38, "vitre")  # vitres
    tronc(m, (-0.72, 0.72, -0.88, 0.5), 1.37, (-0.7, 0.7, -0.85, 0.45), 1.43, C)        # toit
    boite(m, -1.0, -0.88, 1.0, 1.1, 0.35, 0.5, C, -0.1)                                 # rétros
    boite(m, 0.88, 1.0, 1.0, 1.1, 0.35, 0.5, C, -0.1)
    boite(m, -0.95, 0.95, 0.2, 0.5, -2.1, -1.92, "plastique", -0.05)                    # pare-chocs
    boite(m, 0.42, 0.88, 0.58, 0.78, -2.05, -1.99, "feu", -0.1)                         # feux
    boite(m, -0.88, -0.42, 0.58, 0.78, -2.05, -1.99, "feu", -0.1)
    boite(m, -0.28, 0.28, 0.26, 0.4, -2.14, -2.1, "plaque", -0.2)                       # plaque
    boite(m, 0.5, 0.64, 0.17, 0.27, -2.16, -1.95, "chrome", -0.05)                      # échappement
    _roues(m, (-0.95, 0.95), (-1.25, 1.25), 0.33, 0.26)


def _sportive(m):
    C = "carro"
    tronc(m, (-0.98, 0.98, -2.15, 2.15), 0.2, (-0.94, 0.94, -2.1, 2.1), 0.64, C)
    boite(m, -0.85, 0.85, 0.08, 0.22, -2.0, 2.0, "plastique", 1.5)
    tronc(m, (-0.92, 0.92, 0.7, 2.1), 0.64, (-0.8, 0.8, 1.2, 2.05), 0.76, C)           # capot
    tronc(m, (-0.9, 0.9, -2.08, -0.9), 0.64, (-0.84, 0.84, -2.0, -0.95), 0.74, C)      # coffre
    tronc(m, (-0.84, 0.84, -0.95, 0.7), 0.64, (-0.62, 0.62, -0.5, 0.2), 1.08, "vitre")
    tronc(m, (-0.64, 0.64, -0.52, 0.22), 1.07, (-0.62, 0.62, -0.5, 0.2), 1.12, C)
    boite(m, -0.62, -0.5, 0.74, 0.98, -2.0, -1.9, "carbone")                            # aileron
    boite(m, 0.5, 0.62, 0.74, 0.98, -2.0, -1.9, "carbone")
    boite(m, -1.0, 1.0, 0.97, 1.03, -2.2, -1.75, "carbone", -0.1)
    boite(m, -0.82, 0.82, 0.2, 0.4, -2.24, -2.12, "plastique", -0.05)                   # diffuseur
    boite(m, -0.9, 0.9, 0.5, 0.58, -2.2, -2.14, "feu", -0.1)                            # bandeau feux
    boite(m, -0.28, 0.28, 0.24, 0.36, -2.27, -2.24, "plaque", -0.2)
    _roues(m, (-1.0, 1.0), (-1.35, 1.35), 0.36, 0.3)


def _pickup(m):
    C = "carro"
    tronc(m, (-0.95, 0.95, -2.6, 2.6), 0.35, (-0.93, 0.93, -2.58, 2.58), 0.95, C)
    boite(m, -0.8, 0.8, 0.2, 0.36, -2.4, 2.4, "plastique", 1.5)
    tronc(m, (-0.93, 0.93, 1.55, 2.58), 0.95, (-0.88, 0.88, 1.6, 2.5), 1.08, C)        # capot
    tronc(m, (-0.9, 0.9, 0.0, 1.6), 0.95, (-0.78, 0.78, 0.3, 1.2), 1.72, "vitre")       # cabine
    tronc(m, (-0.8, 0.8, 0.26, 1.24), 1.7, (-0.78, 0.78, 0.3, 1.2), 1.77, C)
    boite(m, -0.88, 0.88, 0.95, 1.0, -2.5, 0.0, "plastique", -0.02)                     # benne
    boite(m, -0.96, -0.86, 0.95, 1.42, -2.6, 0.0, C, -0.03)
    boite(m, 0.86, 0.96, 0.95, 1.42, -2.6, 0.0, C, -0.03)
    boite(m, -0.96, 0.96, 0.95, 1.42, -2.62, -2.5, C, -0.05)                            # hayon
    boite(m, -0.98, 0.98, 0.4, 0.64, -2.76, -2.6, "chrome", -0.05)                      # pare-chocs
    boite(m, -0.28, 0.28, 0.44, 0.58, -2.8, -2.76, "plaque", -0.2)
    boite(m, 0.62, 0.92, 1.05, 1.28, -2.66, -2.62, "feu", -0.1)
    boite(m, -0.92, -0.62, 1.05, 1.28, -2.66, -2.62, "feu", -0.1)
    _roues(m, (-1.0, 1.0), (-1.7, 1.5), 0.42, 0.3)


_VOITURES = [_citadine, _sportive, _pickup]


def voiture(idx):
    cle = ("voiture", idx)
    if cle not in _cache:
        m = Maillage()
        _VOITURES[idx](m)
        _cache[cle] = m
    return _cache[cle]


def plateforme():
    if "plateforme" not in _cache:
        m = Maillage()
        anneaux(m, 28, 0, 0, [(2.8, -0.14), (2.8, 0.0)], "plateforme")
        _cache["plateforme"] = m
    return _cache["plateforme"]


# --------------------------------------------------------------------- décor
def _sapin(m, neige):
    anneaux(m, 6, 0, 0, [(0.25, 0), (0.2, 1.8)], "tronc")
    for r0, y0, r1, y1 in ((1.8, 1.2, 0.2, 3.5), (1.5, 2.7, 0.15, 5.0), (1.1, 4.2, 0.1, 6.5)):
        anneaux(m, 8, 0, 0, [(r0, y0), (r1, y1)], "conifere")
        if neige:       # calotte de neige sur le haut de chaque étage
            t = 0.5
            ym = y0 + (y1 - y0) * t
            rm = (r0 + (r1 - r0) * t) * 1.04
            anneaux(m, 8, 0, 0, [(rm, ym), (r1 * 1.04, y1)], "conifere_neige", biais=-0.05)


def _construire_decor(genre, nuit, fenetres):
    m = Maillage()
    if genre == "arbre":
        anneaux(m, 6, 0, 0, [(0.25, 0), (0.2, 2.2)], "tronc")
        anneaux(m, 7, 0, 0, [(0.9, 1.6), (1.9, 2.8), (1.6, 4.1), (0.55, 5.1)], "feuille")
    elif genre == "arbre2":
        anneaux(m, 6, 0, 0, [(0.2, 0), (0.18, 2.4)], "tronc")
        anneaux(m, 7, 0, 0, [(0.5, 1.6), (1.05, 3.2), (0.95, 5.2), (0.35, 6.6)], "feuille2")
    elif genre == "meule":
        anneaux(m, 8, 0, 0, [(1.1, 0), (1.1, 1.5), (0.7, 2.0)], "foin")
    elif genre == "sapin":
        _sapin(m, False)
    elif genre == "sapin_neige":
        _sapin(m, True)
    elif genre == "cactus":
        boite(m, -0.3, 0.3, 0, 3.4, -0.3, 0.3, "cactus")
        boite(m, -1.0, -0.3, 1.4, 1.75, -0.2, 0.2, "cactus")
        boite(m, -1.0, -0.6, 1.4, 2.7, -0.2, 0.2, "cactus")
        boite(m, 0.3, 0.9, 1.9, 2.2, -0.2, 0.2, "cactus")
        boite(m, 0.6, 0.9, 1.9, 3.0, -0.2, 0.2, "cactus")
    elif genre == "rocher":
        anneaux(m, 6, 0, 0, [(1.3, 0), (1.6, 0.8), (0.8, 1.6)], "pierre")
    elif genre == "rocher_neige":
        anneaux(m, 6, 0, 0, [(1.3, 0), (1.6, 0.8), (0.8, 1.6)], "pierre_neige")
    elif genre == "lampadaire":
        anneaux(m, 4, 0, 0, [(0.11, 0), (0.08, 6.5)], "metal")
        boite(m, 0.0, 2.2, 6.3, 6.45, -0.06, 0.06, "metal")
        boite(m, 1.7, 2.3, 6.15, 6.3, -0.2, 0.2, "lampe")
    elif genre.startswith("immeuble"):
        k = int(genre[8:] or 0)
        w, d, h, mat = [(5, 5, 10, "beton1"), (6, 7, 16, "beton2"),
                        (4.5, 6, 8, "beton3"), (7, 5, 20, "beton2")][k % 4]
        boite(m, -w, w, 0, h, -d, d, mat)
        boite(m, -w - 0.2, w + 0.2, h, h + 0.4, -d - 0.2, d + 0.2, "plastique")
        if fenetres:
            rnd = random.Random(k * 31 + 7)
            lignes = min(6, int(h / 4))
            cols = max(2, min(3, int(d / 2.4)))
            for r in range(lignes):
                y0 = 2.0 + r * (h - 3.0) / max(1, lignes)
                for c in range(cols):
                    z0 = -d + (c + 0.5) * (2 * d) / cols - 0.7
                    mat_f = "fenetre_nuit" if (nuit and rnd.random() < 0.55) else "fenetre"
                    m.face([(w + 0.03, y0, z0), (w + 0.03, y0, z0 + 1.4),
                            (w + 0.03, y0 + 1.6, z0 + 1.4), (w + 0.03, y0 + 1.6, z0)],
                           mat_f, (0, h / 2, 0), -0.05)
    return m


def decor(genre, nuit=False, fenetres=True):
    cle = ("decor", genre, nuit, fenetres)
    if cle not in _cache:
        _cache[cle] = _construire_decor(genre, nuit, fenetres)
    return _cache[cle]


def arche():
    """Portique d'arrivée avec bandeau à damier (visible côté caméra)."""
    if "arche" not in _cache:
        m = Maillage()
        boite(m, -7.7, -7.0, 0, 6.6, -0.3, 0.3, "beton2")
        boite(m, 7.0, 7.7, 0, 6.6, -0.3, 0.3, "beton2")
        boite(m, -7.7, 7.7, 5.5, 6.7, -0.3, 0.3, "plastique")
        cols = 24
        largeur = 15.4 / cols
        for r in range(2):
            for c in range(cols):
                x0 = -7.7 + c * largeur
                y0 = 5.5 + r * 0.6
                mat = "damier_n" if (r + c) % 2 == 0 else "damier_b"
                m.face([(x0, y0, -0.32), (x0 + largeur, y0, -0.32),
                        (x0 + largeur, y0 + 0.6, -0.32), (x0, y0 + 0.6, -0.32)],
                       mat, (0, 6.1, 0.0), -0.1)
        _cache["arche"] = m
    return _cache["arche"]
