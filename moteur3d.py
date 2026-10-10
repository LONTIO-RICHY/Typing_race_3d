"""Petit moteur 3D logiciel : caméra, maillages, éclairage, brume.

Tout est calculé en Python pur puis dessiné avec des polygones Tkinter :
projection en perspective, faces cachées supprimées, ombrage selon la
lumière (diffus + reflet brillant), brume de distance.
"""

import math
from functools import lru_cache

from config import H, W


# ------------------------------------------------------------------ couleurs
@lru_cache(maxsize=8192)
def hex_rgb(h):
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


def rgb_hex(r, g, b):
    r = 0 if r < 0 else 255 if r > 255 else int(r)
    g = 0 if g < 0 else 255 if g > 255 else int(g)
    b = 0 if b < 0 else 255 if b > 255 else int(b)
    return "#%02x%02x%02x" % (r, g, b)


def melanger(h1, h2, t):
    if t <= 0:
        return h1
    if t >= 1:
        return h2
    a, b = hex_rgb(h1), hex_rgb(h2)
    return rgb_hex(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t,
                   a[2] + (b[2] - a[2]) * t)


def normaliser(v):
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


# ------------------------------------------------------------------ matériaux
# couleur None = couleur de carrosserie ; emissif = brille sans ombrage
MATERIAUX = {
    "carro": {"couleur": None, "spec": 0.8, "brill": 26},
    "vitre": {"couleur": "#16222e", "spec": 1.0, "brill": 40},
    "pneu": {"couleur": "#17181a", "spec": 0.05, "brill": 4},
    "jante": {"couleur": "#b3b9c0", "spec": 0.9, "brill": 30},
    "plastique": {"couleur": "#26282c", "spec": 0.2, "brill": 8},
    "carbone": {"couleur": "#1c1d21", "spec": 0.8, "brill": 34},
    "chrome": {"couleur": "#cdd4db", "spec": 1.0, "brill": 50},
    "plaque": {"couleur": "#f2f2ee", "spec": 0.1, "brill": 6},
    "feu": {"couleur": "#d61f1f", "emissif": True},
    "tronc": {"couleur": "#5b3e27", "spec": 0.0, "brill": 2},
    "feuille": {"couleur": "#2f7d32", "spec": 0.05, "brill": 4},
    "feuille2": {"couleur": "#3c8f3a", "spec": 0.05, "brill": 4},
    "conifere": {"couleur": "#1f5a36", "spec": 0.0, "brill": 2},
    "conifere_neige": {"couleur": "#e3ecf4", "spec": 0.2, "brill": 6},
    "cactus": {"couleur": "#3f8f4c", "spec": 0.05, "brill": 4},
    "pierre": {"couleur": "#8c8479", "spec": 0.05, "brill": 4},
    "pierre_neige": {"couleur": "#d3dbe3", "spec": 0.2, "brill": 6},
    "foin": {"couleur": "#d9b44a", "spec": 0.0, "brill": 2},
    "beton1": {"couleur": "#b9bdc3", "spec": 0.1, "brill": 6},
    "beton2": {"couleur": "#a2a9b4", "spec": 0.1, "brill": 6},
    "beton3": {"couleur": "#c9b89e", "spec": 0.1, "brill": 6},
    "fenetre": {"couleur": "#5f7f9c", "spec": 0.9, "brill": 30},
    "fenetre_nuit": {"couleur": "#ffd27a", "emissif": True},
    "metal": {"couleur": "#59616b", "spec": 0.6, "brill": 20},
    "lampe": {"couleur": "#fff1b8", "emissif": True},
    "plateforme": {"couleur": "#2b3446", "spec": 0.6, "brill": 22},
    "damier_n": {"couleur": "#141414", "emissif": True},
    "damier_b": {"couleur": "#f4f4f4", "emissif": True},
}


class Eclairage:
    def __init__(self, piste):
        self.lumiere = normaliser(piste["lumiere"])
        self.ambiant = piste["ambiant"]
        self.diffus = piste["diffus"]
        self.remplissage = 0.22
        self.speculaire = 0.75
        self.teinte = piste.get("teinte", (1.0, 1.0, 1.0))
        self.brume = piste["brume"]
        self.brume_debut = 22.0
        self.brume_fin = 120.0
        self.brume_max = 0.9 if not piste.get("nuit") else 0.8

    def brumer(self, couleur, dist):
        t = (dist - self.brume_debut) / (self.brume_fin - self.brume_debut)
        if t <= 0:
            return couleur
        t = (1.0 if t > 1 else t) * self.brume_max
        return melanger(couleur, self.brume, t)


# ------------------------------------------------------------------ caméra
class Camera:
    def __init__(self, x=0.0, y=3.0, z=-8.0, pitch=0.12, focale=520.0, cx=W / 2, cy=268.0):
        self.x, self.y, self.z = x, y, z
        self.pitch, self.focale, self.cx, self.cy = pitch, focale, cx, cy
        self.maj()

    def maj(self):
        self.cp = math.cos(self.pitch)
        self.sp = math.sin(self.pitch)

    def horizon(self):
        return self.cy - self.focale * math.tan(self.pitch)

    def proj(self, X, Y, Z):
        """Point 3D -> (x écran, y écran, profondeur) ou None s'il est derrière."""
        rx, ry, rz = X - self.x, Y - self.y, Z - self.z
        zc = -ry * self.sp + rz * self.cp
        if zc < 0.4:
            return None
        yc = ry * self.cp + rz * self.sp
        f = self.focale / zc
        return (self.cx + rx * f, self.cy - yc * f, zc)


# ------------------------------------------------------------------ maillages
def _normale(pts):
    nx = ny = nz = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1, z1 = pts[i]
        x2, y2, z2 = pts[(i + 1) % n]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    l = math.sqrt(nx * nx + ny * ny + nz * nz)
    if l < 1e-9:
        return None
    return (nx / l, ny / l, nz / l)


class Maillage:
    """Liste de faces : (points, matériau, normale, centre, biais, double_face)."""

    def __init__(self):
        self.faces = []

    def face(self, pts, mat, solide=None, biais=0.0, double=False):
        n = _normale(pts)
        if n is None:
            return
        k = len(pts)
        c = (sum(p[0] for p in pts) / k, sum(p[1] for p in pts) / k, sum(p[2] for p in pts) / k)
        if solide is not None and not double:
            if n[0] * (c[0] - solide[0]) + n[1] * (c[1] - solide[1]) + n[2] * (c[2] - solide[2]) < 0:
                n = (-n[0], -n[1], -n[2])
        self.faces.append((pts, mat, n, c, biais, double))


def tronc(m, bas, y0, haut, y1, mats, biais=0.0):
    """Tronc de pavé : 'bas' et 'haut' = (x0, x1, z0, z1). z0 = arrière, z1 = avant."""
    if isinstance(mats, str):
        mats = {"*": mats}
    bx0, bx1, bz0, bz1 = bas
    hx0, hx1, hz0, hz1 = haut
    b = [(bx0, y0, bz0), (bx1, y0, bz0), (bx1, y0, bz1), (bx0, y0, bz1)]
    t = [(hx0, y1, hz0), (hx1, y1, hz0), (hx1, y1, hz1), (hx0, y1, hz1)]
    pts = b + t
    centre = (sum(p[0] for p in pts) / 8, sum(p[1] for p in pts) / 8, sum(p[2] for p in pts) / 8)
    faces = {
        "arriere": (b[0], b[1], t[1], t[0]),
        "droite": (b[1], b[2], t[2], t[1]),
        "avant": (b[2], b[3], t[3], t[2]),
        "gauche": (b[3], b[0], t[0], t[3]),
        "dessus": (t[0], t[1], t[2], t[3]),
    }
    for nom, f in faces.items():
        mat = mats.get(nom, mats.get("*"))
        if mat:
            m.face(list(f), mat, centre, biais)


def boite(m, x0, x1, y0, y1, z0, z1, mats, biais=0.0):
    tronc(m, (x0, x1, z0, z1), y0, (x0, x1, z0, z1), y1, mats, biais)


def anneaux(m, n, cx, cz, rings, mat_flanc, mat_dessus=None, rot=0.0, biais=0.0):
    """Solide de révolution autour de l'axe vertical : rings = [(rayon, hauteur), ...]."""
    rs = []
    for r, y in rings:
        rs.append([(cx + r * math.cos(rot + 2 * math.pi * j / n), y,
                    cz + r * math.sin(rot + 2 * math.pi * j / n)) for j in range(n)])
    ys = [y for _, y in rings]
    solide = (cx, (min(ys) + max(ys)) / 2, cz)
    for i in range(len(rings) - 1):
        a, b = rs[i], rs[i + 1]
        for j in range(n):
            k = (j + 1) % n
            m.face([a[j], a[k], b[k], b[j]], mat_flanc, solide, biais)
    m.face(rs[-1], mat_dessus or mat_flanc, solide, biais)


def cylindre_x(m, cx, cy, cz, r, larg, n, mat_pneu, mat_jante, biais=0.0):
    """Roue : cylindre dont l'axe est horizontal (axe x)."""
    x0, x1 = cx - larg / 2, cx + larg / 2
    ring = [(cy + r * math.cos(2 * math.pi * j / n), cz + r * math.sin(2 * math.pi * j / n))
            for j in range(n)]
    solide = (cx, cy, cz)
    for j in range(n):
        k = (j + 1) % n
        m.face([(x0, ring[j][0], ring[j][1]), (x1, ring[j][0], ring[j][1]),
                (x1, ring[k][0], ring[k][1]), (x0, ring[k][0], ring[k][1])],
               mat_pneu, solide, biais)
    for x, ext in ((x0, -1), (x1, 1)):
        m.face([(x, y, z) for y, z in ring], mat_pneu, solide, biais)
        petit = [(x + ext * 0.012, cy + (y - cy) * 0.62, cz + (z - cz) * 0.62) for y, z in ring]
        m.face(petit, mat_jante, solide, biais - 0.02)


# ------------------------------------------------------------------ rendu
def rendre(cam, maillage, pos, ecl, couleur_carro=None, yaw=0.0, echelle=1.0,
           feux="#e8262a", biais_global=0.0):
    """Transforme un maillage en polygones écran triés du plus loin au plus proche.

    Retourne une liste de (profondeur, [x1, y1, x2, y2, ...], couleur).
    """
    px, py, pz = pos
    co, si = math.cos(yaw), math.sin(yaw)
    camx, camy, camz = cam.x, cam.y, cam.z
    L = ecl.lumiere
    tr, tg, tb = ecl.teinte
    ambiant, diffus, remp, spec_g = ecl.ambiant, ecl.diffus, ecl.remplissage, ecl.speculaire
    sortie = []
    for pts, mat, nrm, ctr, biais, double in maillage.faces:
        nx, ny, nz = nrm
        n = (nx * co + nz * si, ny, -nx * si + nz * co)
        cx_, cy_, cz_ = ctr
        c = (px + (cx_ * co + cz_ * si) * echelle, py + cy_ * echelle,
             pz + (-cx_ * si + cz_ * co) * echelle)
        vx, vy, vz = camx - c[0], camy - c[1], camz - c[2]
        dist = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
        vx, vy, vz = vx / dist, vy / dist, vz / dist
        nv = n[0] * vx + n[1] * vy + n[2] * vz
        if nv <= 0:
            if not double:
                continue
            n = (-n[0], -n[1], -n[2])
            nv = -nv
        coords = []
        prof = 0.0
        ok = True
        for (x, y, z) in pts:
            X = px + (x * co + z * si) * echelle
            Y = py + y * echelle
            Z = pz + (-x * si + z * co) * echelle
            rx, ry, rz = X - camx, Y - camy, Z - camz
            zc = -ry * cam.sp + rz * cam.cp
            if zc < 0.4:
                ok = False
                break
            yc = ry * cam.cp + rz * cam.sp
            f = cam.focale / zc
            coords.append(cam.cx + rx * f)
            coords.append(cam.cy - yc * f)
            prof += zc
        if not ok:
            continue
        # faces inutiles : hors de l'écran, ou plus petites qu'un pixel (loin) -> moins de polygones à dessiner
        xs, ys = coords[0::2], coords[1::2]
        minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
        if maxx < 0 or minx > W or maxy < 0 or miny > H:
            continue
        if maxx - minx < 1.2 and maxy - miny < 1.2:
            continue
        prof = prof / len(pts) + biais + biais_global

        m = MATERIAUX[mat]
        base = couleur_carro if mat == "carro" else m["couleur"]
        if mat == "feu":
            base = feux
        if base is None:
            base = "#808080"
        r, g, b = hex_rgb(base)
        if m.get("emissif"):
            col = base
        else:
            dl = n[0] * L[0] + n[1] * L[1] + n[2] * L[2]
            inten = ambiant + diffus * (dl if dl > 0 else 0.0) + remp * nv
            r, g, b = r * inten * tr, g * inten * tg, b * inten * tb
            s = m.get("spec", 0.0)
            if s > 0:
                hx, hy, hz = L[0] + vx, L[1] + vy, L[2] + vz
                hl = math.sqrt(hx * hx + hy * hy + hz * hz) or 1.0
                nh = (n[0] * hx + n[1] * hy + n[2] * hz) / hl
                if nh > 0:
                    sp = (nh ** m["brill"]) * s * spec_g * 255
                    r, g, b = r + sp, g + sp, b + sp
            col = rgb_hex(r, g, b)
        col = ecl.brumer(col, dist)
        sortie.append((prof, coords, col))
    sortie.sort(key=lambda e: -e[0])
    return sortie
