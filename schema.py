"""Dessins des compétitions : trophée, médailles, schéma du tableau (coupe du monde) et parcours (championnat).

Tout est dessiné avec les formes du Peintre (pas d'image) : ça s'adapte à la taille de la fenêtre.
"""

import math

from config import ACCENT, BORD, CARTE, CARTE_HAUT, FOND, GRIS, JAUNE, ROUGE, VERT
from moteur3d import melanger

OR, OR_FONCE, OR_CLAIR = "#fbbf24", "#b45309", "#fde68a"

# place -> (nom, couleur principale, couleur foncée, couleur claire)
MEDAILLES = {
    1: ("Trophée d'or", "#fbbf24", "#b45309", "#fde68a"),
    2: ("Médaille d'argent", "#cbd5e1", "#64748b", "#f1f5f9"),
    3: ("Médaille de bronze", "#d08a4e", "#7c4a1e", "#f0b98a"),
}
RUBANS = {2: ("#3b82f6", "#1d4ed8"), 3: ("#ef4444", "#b91c1c")}

# phrase affichée à côté de la position (« 1er · Tu es le meilleur... »)
PHRASES = {
    1: "Tu es le meilleur en saisie de frappe !",
    2: "Tu es parmi les meilleurs en saisie de frappe !",
    3: "Tu es parmi les meilleurs en saisie de frappe !",
}


def ordinal(n):
    return "1er" if n == 1 else f"{n}e"


def phrase_podium(place):
    return f"{ordinal(place)}  ·  {PHRASES[place]}"


# ------------------------------------------------------------------ trophée et médailles
def dessiner_trophee(p, cx, cy, s=1.0, actif=True, now=None, fond=CARTE):
    """Coupe dorée centrée en (cx, cy). s = échelle (1.0 ≈ 100 px de haut). actif=False : coupe grisée."""
    c1, c2, c3 = (OR, OR_FONCE, OR_CLAIR) if actif else ("#5b6785", "#3a4566", "#7d8aab")
    if actif and now is not None:
        pulse = 1.0 + 0.06 * math.sin(now * 3.0)
        for r, t in ((80, 0.05), (62, 0.10), (46, 0.18)):               # halo doré qui respire
            rr = r * s * pulse
            p.oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=melanger(fond, OR, t))
    larg = max(2, 5 * s)
    for sens in (-1, 1):                                                  # anses
        p.oval(cx + sens * 34 * s - 12 * s, cy - 36 * s, cx + sens * 34 * s + 12 * s, cy - 6 * s,
               outline=c2, width=larg)
    p.rect(cx - 24 * s, cy + 40 * s, cx + 24 * s, cy + 51 * s, r=3, fill=c2)       # socle
    p.rect(cx - 16 * s, cy + 31 * s, cx + 16 * s, cy + 42 * s, fill=c1)
    p.rect(cx - 5 * s, cy + 8 * s, cx + 5 * s, cy + 33 * s, fill=c2)               # pied
    gauche, droite = [], []
    n = 8
    for i in range(n + 1):                                                # coupe arrondie
        u = i / n
        y = cy - 42 * s + u * 52 * s
        w = 30 * s * (1 - 0.78 * u ** 1.6)
        gauche.append((cx - w, y))
        droite.append((cx + w, y))
    pts = [v for q in gauche + droite[::-1] for v in q]
    p.poly(pts, fill=c1, outline=c2, width=2)
    p.rect(cx - 33 * s, cy - 48 * s, cx + 33 * s, cy - 40 * s, r=3, fill=c3, outline=c2, width=1)   # bord
    p.poly([cx - 22 * s, cy - 36 * s, cx - 15 * s, cy - 36 * s, cx - 13 * s, cy - 4 * s, cx - 18 * s, cy - 6 * s],
           fill=c3)                                                       # reflet
    p.texte(cx + 3 * s, cy - 20 * s, text="★", fill=c2, font=("Segoe UI", max(6, round(22 * s)), "bold"))
    if actif and now is not None:                                          # étincelles qui tournent
        for k in range(6):
            a = now * 0.8 + k * math.pi / 3
            r = (64 + 6 * math.sin(now * 3 + k)) * s
            p.texte(cx + r * math.cos(a), cy - 4 * s + r * math.sin(a) * 0.8, text="✦", fill=c3,
                    font=("Segoe UI", max(6, round(11 * s))))


def dessiner_medaille(p, cx, cy, s, rang):
    """Médaille d'argent (rang 2) ou de bronze (rang 3), avec son ruban."""
    _nom, c1, c2, c3 = MEDAILLES[rang]
    r1, r2 = RUBANS[rang]
    p.poly([cx - 30 * s, cy - 60 * s, cx - 8 * s, cy - 60 * s, cx + 11 * s, cy - 8 * s, cx - 11 * s, cy - 8 * s],
           fill=r1)
    p.poly([cx + 30 * s, cy - 60 * s, cx + 8 * s, cy - 60 * s, cx - 11 * s, cy - 8 * s, cx + 11 * s, cy - 8 * s],
           fill=r2)
    p.oval(cx - 34 * s, cy - 24 * s, cx + 34 * s, cy + 44 * s, fill=c1, outline=c2, width=max(2, 4 * s))
    p.oval(cx - 26 * s, cy - 16 * s, cx + 26 * s, cy + 36 * s, outline=c3, width=max(1, 2 * s))
    p.texte(cx, cy + 10 * s, text=str(rang), fill=c2, font=("Segoe UI", max(8, round(34 * s)), "bold"))


def dessiner_recompense(p, cx, cy, s, place, now=None):
    """Trophée (1re place) ou médaille (2e, 3e). Ne dessine rien pour les autres places."""
    if place == 1:
        dessiner_trophee(p, cx, cy, s, True, now)
    elif place in (2, 3):
        dessiner_medaille(p, cx, cy, s, place)


# ------------------------------------------------------------------ coupe du monde : le tableau
def effectifs(nb):
    """Nombre de voitures à chaque tour : 32 -> [32, 16, 8, 4, 2]."""
    liste, m = [], nb
    while True:
        liste.append(m)
        if m <= 2:
            return liste
        m = (m + 1) // 2


def nom_court(m):
    if m <= 2:
        return "Finale"
    if m <= 4:
        return "Demies"
    if m <= 8:
        return "Quarts"
    if m <= 16:
        return "8es"
    return "16es"


def _pastille(p, cx, cy, w, h, texte, fond, fg, taille=8):
    p.rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, r=h / 2, fill=fond)
    p.texte(cx, cy, text=texte, fill=fg, font=("Segoe UI", taille, "bold"))


def dessiner_schema_cdm(p, c, x0, y0, x1, y1, now):
    """Tableau de la coupe du monde : 16es -> 8es -> quarts -> demies -> finale -> trophée.

    Le chemin du joueur est en vert, sa position actuelle est marquée « TOI »
    (bleu = prochain tour, rouge = éliminé, or = champion du monde).
    """
    ms = effectifs(c.nb)
    nt = len(ms)
    joue = ms.index(len(c.dernier_rang)) if c.dernier_rang and len(c.dernier_rang) in ms else -1
    sorti = c.joueur_sorti
    champion = c.fini and not sorti
    if champion:
        pos = nt                                   # sur le trophée
        passes = set(range(nt))
    elif sorti:
        pos = max(0, joue)
        passes = set(range(0, max(0, joue)))
    else:
        pos = min(nt - 1, joue + 1)
        passes = set(range(0, joue + 1))

    marge_g, marge_d = 38, 46
    pas_x = (x1 - x0 - marge_g - marge_d) / nt
    xs = [x0 + marge_g + i * pas_x for i in range(nt + 1)]
    ya, yb = y0 + 42, y1 - 8
    ymid = (ya + yb) / 2

    def y_slot(i, k):
        if i >= nt:
            return ymid
        return ya + (k + 0.5) * (yb - ya) / ms[i]

    larg = max(10.0, min(30.0, pas_x * 0.42))
    s0 = c.nb // 2                                  # case symbolique du joueur dans le tableau
    chemin = [s0 >> i for i in range(nt)]

    # titres des colonnes
    for i in range(nt + 1):
        if i == nt:
            nom, sous, col = "Trophée", "", JAUNE if champion else GRIS
        else:
            nom, sous = nom_court(ms[i]), f"{ms[i]} pilotes"
            col = VERT if i in passes else ((ROUGE if sorti else ACCENT) if i == pos else GRIS)
        p.texte(xs[i], y0 + 12, text=nom, fill=col, font=("Segoe UI", 10, "bold"))
        if sous:
            p.texte(xs[i], y0 + 26, text=sous, fill=GRIS, font=("Segoe UI", 8))

    # liens du tableau (tous en sombre, puis le chemin du joueur en vert)
    for i in range(nt):
        for k in range(ms[i]):
            ya_, yb_ = y_slot(i, k), y_slot(i + 1, k // 2)
            xa, xb = xs[i] + larg / 2, xs[i + 1] - (larg / 2 if i + 1 < nt else 14)
            xm = (xa + xb) / 2
            p.ligne(xa, ya_, xm, ya_, xm, yb_, xb, yb_, fill=BORD, width=1)
    for i in sorted(passes):
        if i >= nt:
            continue
        ya_, yb_ = y_slot(i, chemin[i]), y_slot(i + 1, chemin[i] // 2 if i + 1 < nt else 0)
        xa, xb = xs[i] + larg / 2, xs[i + 1] - (larg / 2 if i + 1 < nt else 14)
        xm = (xa + xb) / 2
        p.ligne(xa, ya_, xm, ya_, xm, yb_, xb, yb_, fill=VERT, width=3)

    # cases
    for i in range(nt):
        haut = max(2.0, min(12.0, (yb - ya) / ms[i] * 0.7))
        for k in range(ms[i]):
            y = y_slot(i, k)
            p.rect(xs[i] - larg / 2, y - haut / 2, xs[i] + larg / 2, y + haut / 2, r=min(4, haut / 2),
                   fill=CARTE_HAUT, outline=BORD, width=1)
        if i in passes:
            y = y_slot(i, chemin[i])
            hh = max(haut, 6.0)
            p.rect(xs[i] - larg / 2, y - hh / 2, xs[i] + larg / 2, y + hh / 2, r=min(4, hh / 2),
                   fill=VERT, outline=VERT, width=1)

    # trophée au bout du tableau
    s = max(0.3, min(0.62, (yb - ya) / 150))
    dessiner_trophee(p, xs[nt], ymid, s, actif=champion, now=now if champion else None)

    # marqueur « TOI » : là où tu en es
    if pos >= nt:
        _pastille(p, xs[nt], ymid - 50 * s - 12, 38, 16, "TOI", OR, FOND)
    else:
        y = y_slot(pos, chemin[pos])
        if sorti:
            _pastille(p, xs[pos], y, 46, 17, "TOI ✖", ROUGE, "#ffffff")
        else:
            gonfle = 2 + 2 * math.sin(now * 5)
            p.rect(xs[pos] - 20 - gonfle, y - 10 - gonfle, xs[pos] + 20 + gonfle, y + 10 + gonfle, r=11,
                   outline=ACCENT, width=2)
            _pastille(p, xs[pos], y, 38, 17, "TOI", ACCENT, FOND)


# ------------------------------------------------------------------ championnat : la route vers le trophée
def dessiner_schema_champ(p, c, x0, y0, x1, y1, now, rang, pts):
    """Manches jouées (vert), prochaine manche (bleu) et trophée, avec ta position et tes points."""
    n, faites = c.manches, c.manche
    champion = c.fini and rang == 1
    marge_g, marge_d = 40, 100
    xs = [x0 + marge_g + i * (x1 - x0 - marge_g - marge_d) / max(1, n - 1) for i in range(n)]
    cy = y0 + (y1 - y0) * 0.38
    p.texte(x0 + 6, y0 + 4, text="Route vers le trophée", anchor="w", fill=GRIS, font=("Segoe UI", 9, "bold"))
    xt = x1 - 36
    p.ligne(xs[0], cy, xt - 20, cy, fill=BORD, width=3)
    if faites > 1:
        p.ligne(xs[0], cy, xs[min(faites, n) - 1], cy, fill=VERT, width=4)
    if faites >= n:
        p.ligne(xs[-1], cy, xt - 20, cy, fill=VERT, width=4)
    for i, x in enumerate(xs):
        if i < faites:
            p.oval(x - 13, cy - 13, x + 13, cy + 13, fill=VERT, outline=VERT)
            col = FOND
        elif i == faites:
            g = 2 + 2 * math.sin(now * 5)
            p.oval(x - 13 - g, cy - 13 - g, x + 13 + g, cy + 13 + g, outline=ACCENT, width=2)
            p.oval(x - 13, cy - 13, x + 13, cy + 13, fill=CARTE_HAUT, outline=ACCENT, width=2)
            col = ACCENT
        else:
            p.oval(x - 13, cy - 13, x + 13, cy + 13, fill=CARTE_HAUT, outline=BORD, width=2)
            col = GRIS
        p.texte(x, cy, text=str(i + 1), fill=col, font=("Segoe UI", 11, "bold"))
    p.texte(xs[0] - 4, cy + 24, text="manches", anchor="w", fill=GRIS, font=("Segoe UI", 8))
    dessiner_trophee(p, xt, cy + 4, 0.42, actif=champion, now=now if champion else None)
    # position actuelle sous la dernière manche jouée
    i = max(0, min(n, faites) - 1)
    col = OR if rang == 1 else (ACCENT if rang <= 3 else "#e2e8f0")
    _pastille(p, xs[i], cy + 34, 118, 17, f"TOI · {ordinal(rang)} · {pts} pts", col, FOND, 8)
