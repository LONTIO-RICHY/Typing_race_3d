"""Claviers virtuels (AZERTY, QWERTY...), détection du clavier système, mains guides."""

import math
import platform
import subprocess

# 3 rangées de 10 touches : haut, base (repos), bas
LAYOUTS = {
    "azerty": {"nom": "AZERTY", "pays": "France, Belgique, Afrique francophone",
               "rangees": ["azertyuiop", "qsdfghjklm", "wxcvbn,;:!"]},
    "qwerty": {"nom": "QWERTY", "pays": "États-Unis, Royaume-Uni, international",
               "rangees": ["qwertyuiop", "asdfghjkl;", "zxcvbnm,./"]},
    "qwertz": {"nom": "QWERTZ", "pays": "Allemagne, Suisse, Autriche",
               "rangees": ["qwertzuiop", "asdfghjklö", "yxcvbnm,.-"]},
    "dvorak": {"nom": "DVORAK", "pays": "Disposition optimisée (États-Unis)",
               "rangees": ["',.pyfgcrl", "aoeuidhtns", ";qjkxbmwvz"]},
    "colemak": {"nom": "COLEMAK", "pays": "Disposition moderne (États-Unis)",
                "rangees": ["qwfpgjluy;", "arstdhneio", "zxcvbkm,./"]},
}
ORDRE = ["azerty", "qwerty", "qwertz", "dvorak", "colemak"]

# colonne -> doigt (0..3 main gauche : auriculaire..index ; 4..7 main droite : index..auriculaire)
COL_DOIGT = [0, 1, 2, 3, 3, 4, 4, 5, 6, 7]
COLS_REPOS = [0, 1, 2, 3, 6, 7, 8, 9]       # touches de la rangée de base où reposent les 8 doigts
COLS_REPERES = (3, 6)                        # les index : les deux petites barres du clavier
NOMS_DOIGTS = ["Auriculaire gauche", "Annulaire gauche", "Majeur gauche", "Index gauche",
               "Index droit", "Majeur droit", "Annulaire droit", "Auriculaire droit", "Pouce"]
NOMS_COURTS = ["Auriculaire", "Annulaire", "Majeur", "Index", "Index", "Majeur", "Annulaire", "Auriculaire"]
DOIGT_POUCE = 8


# ------------------------------------------------------------------ détection
def clavier_depuis_hkl(hkl):
    """Déduit la disposition d'un identifiant de clavier Windows (HKL)."""
    langid = hkl & 0xFFFF
    variante = (hkl >> 16) & 0x0FFF
    primaire = langid & 0x3FF
    if langid == 0x0409 and variante == 0x0002:
        return "dvorak"
    if primaire == 0x0C:                        # français
        if langid == 0x0C0C:
            return "qwerty"                     # Canada (CSF)
        if langid == 0x100C:
            return "qwertz"                     # Suisse romande
        return "azerty"
    if langid == 0x0813:
        return "azerty"                         # néerlandais (Belgique)
    if primaire in (0x07, 0x05, 0x0E, 0x1B, 0x24, 0x1A):   # allemand, tchèque, hongrois...
        return "qwertz"
    return "qwerty"


def clavier_depuis_xkb(layout, variante=""):
    layout, variante = layout.lower(), variante.lower()
    if "dvorak" in variante:
        return "dvorak"
    if "colemak" in variante:
        return "colemak"
    if layout in ("fr", "be"):
        return "azerty"
    if layout in ("de", "ch", "at", "cz", "sk", "hu", "si", "hr"):
        return "qwertz"
    return "qwerty"


def detecter_clavier():
    """Retourne (id_disposition, explication) pour le clavier du système."""
    systeme = platform.system()
    try:
        if systeme == "Windows":
            import ctypes
            hkl = ctypes.windll.user32.GetKeyboardLayout(0) & 0xFFFFFFFF
            return clavier_depuis_hkl(hkl), f"Windows (code langue {hkl & 0xFFFF:04X})"
        if systeme == "Linux":
            sortie = subprocess.run(["setxkbmap", "-query"], capture_output=True,
                                    text=True, timeout=2).stdout
            infos = {}
            for ligne in sortie.splitlines():
                if ":" in ligne:
                    cle, val = ligne.split(":", 1)
                    infos[cle.strip()] = val.strip()
            if infos.get("layout"):
                layout = infos["layout"].split(",")[0]
                variante = infos.get("variant", "").split(",")[0]
                return clavier_depuis_xkb(layout, variante), f"Linux (disposition « {layout} »)"
        if systeme == "Darwin":
            sortie = subprocess.run(
                ["defaults", "read", "com.apple.HIToolbox", "AppleCurrentKeyboardLayoutInputSourceID"],
                capture_output=True, text=True, timeout=2).stdout.lower()
            if "french" in sortie or "belgian" in sortie:
                return "azerty", "macOS"
            if "german" in sortie or "swiss" in sortie:
                return "qwertz", "macOS"
            if "dvorak" in sortie:
                return "dvorak", "macOS"
            if "colemak" in sortie:
                return "colemak", "macOS"
            return "qwerty", "macOS"
    except Exception:
        pass
    return "qwerty", "détection impossible, QWERTY proposé"


# ------------------------------------------------------------------ géométrie
class Clavier:
    DECALAGES = (0.0, 0.28, 0.78)       # décalage de chaque rangée, comme un vrai clavier

    def __init__(self, layout_id, x0, y0, pas=58):
        self.id = layout_id
        self.nom = LAYOUTS[layout_id]["nom"]
        self.rangees = LAYOUTS[layout_id]["rangees"]
        self.x0, self.y0, self.pas = x0, y0, pas
        self.t = pas - 6
        self.touches = {}                # caractère -> (cx, cy, rangée, colonne)
        for r, ligne in enumerate(self.rangees):
            for c, ch in enumerate(ligne):
                self.touches[ch] = (x0 + (c + self.DECALAGES[r]) * pas + self.t / 2,
                                    y0 + r * pas + self.t / 2, r, c)
        self.espace = (x0 + pas * 5.1, y0 + 3 * pas + self.t / 2, pas * 5.6, self.t)

    def pos(self, ch):
        if ch == " ":
            return (self.espace[0], self.espace[1])
        t = self.touches.get(ch)
        return (t[0], t[1]) if t else None

    def doigt(self, ch):
        if ch == " ":
            return DOIGT_POUCE
        t = self.touches.get(ch)
        return COL_DOIGT[t[3]] if t else None

    def repos(self, doigt):
        """Centre de la touche de repos d'un doigt (rangée de base)."""
        c = COLS_REPOS[doigt]
        return (self.x0 + (c + self.DECALAGES[1]) * self.pas + self.t / 2,
                self.y0 + self.pas + self.t / 2)

    def lettres(self):
        return {ch for ch in self.touches if ch.isascii() and ch.isalpha()}


# ------------------------------------------------------------------ dessin du clavier
def dessiner_clavier(p, kb, reveles=None, masque=True, flashs=None, nouvelles=()):
    """Dessine le clavier. masque=True : les touches n'affichent leur lettre que si 'reveles'."""
    reveles = reveles or set()
    flashs = flashs or {}
    t = kb.t
    police = ("Consolas", max(8, int(t * 0.40)), "bold")

    def touche(ch, cx, cy, w, h, label):
        visible = (not masque) or ch in reveles
        fond, bord, txt = ("#2b3f8c", "#5b7bd5", "#ffffff") if visible else ("#141d45", "#2b3a78", "#ffffff")
        if ch in nouvelles and not masque:
            fond, bord, txt = "#7a5c00", "#facc15", "#fde68a"
        if ch in flashs:
            fond = flashs[ch]
            txt = "#0b1d3a" if fond in (JAUNE_FLASH, "#4ade80") else "#ffffff"
            bord = "#ffffff"
        p.rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, fill=fond, outline=bord, width=2)
        if visible or ch in flashs:
            p.texte(cx, cy, text=label, fill=txt, font=police)

    for ch, (cx, cy, r, c) in kb.touches.items():
        touche(ch, cx, cy, t, t, ch.upper())
        if r == 1 and c in COLS_REPERES:             # petite barre repère de l'index
            p.rect(cx - t * 0.18, cy + t * 0.30, cx + t * 0.18, cy + t * 0.36, fill="#9fb3d9")
    ex, ey, ew, eh = kb.espace
    touche(" ", ex, ey, ew, eh, "ESPACE")


JAUNE_FLASH = "#eab308"


# ------------------------------------------------------------------ mains guides
LONGUEURS = [1.45, 1.70, 1.85, 1.70, 1.70, 1.85, 1.70, 1.45]      # longueur des doigts (en touches)
LARGEURS = [0.27, 0.31, 0.33, 0.32, 0.32, 0.33, 0.31, 0.27]
PEAU, PEAU_BORD = "#f1c9a5", "#b98560"
ACTIF, ACTIF_BORD = "#facc15", "#d4a017"


def _capsule(a, b, w):
    ax, ay = a
    bx, by = b
    ang = math.atan2(by - ay, bx - ax)
    r = w / 2
    pts = []
    for i in range(9):
        t = ang - math.pi / 2 + math.pi * i / 8
        pts += [bx + r * math.cos(t), by + r * math.sin(t)]
    for i in range(9):
        t = ang + math.pi / 2 + math.pi * i / 8
        pts += [ax + r * math.cos(t), ay + r * math.sin(t)]
    return pts


class Mains:
    """Deux mains semi-transparentes posées sur la rangée de base ; le doigt actif s'étire."""

    def __init__(self, kb):
        self.kb = kb
        self.tips = {f: list(kb.repos(f)) for f in range(8)}
        sx, sy = kb.pos(" ")
        self.pouces = [[sx - kb.pas * 1.0, sy], [sx + kb.pas * 1.0, sy]]

    def maj(self, dt, doigt=None, cible=None):
        kb = self.kb
        k = min(1.0, dt * 16)
        for f in range(8):
            cx, cy = cible if (f == doigt and cible) else kb.repos(f)
            self.tips[f][0] += (cx - self.tips[f][0]) * k
            self.tips[f][1] += (cy - self.tips[f][1]) * k
        sx, sy = kb.pos(" ")
        cible_pouce = (sx + kb.pas * 1.0, sy + (8 if doigt == DOIGT_POUCE else 0))
        self.pouces[1][0] += (cible_pouce[0] - self.pouces[1][0]) * k
        self.pouces[1][1] += (cible_pouce[1] - self.pouces[1][1]) * k

    def dessiner(self, p, doigt=None, noms=False):
        kb, pas = self.kb, self.kb.pas
        for main in (0, 1):
            doigts = range(0, 4) if main == 0 else range(4, 8)
            xs = [kb.repos(f)[0] for f in doigts]
            centre = sum(xs) / 4
            bases = {}
            for f in doigts:
                kx, ky = kb.repos(f)
                bases[f] = (centre + (kx - centre) * 0.72, ky + pas * LONGUEURS[f])
            bx = [b[0] for b in bases.values()]
            by = [b[1] for b in bases.values()]
            haut = sum(by) / 4 - 10
            bas = sum(by) / 4 + pas * 1.5
            xmin, xmax = min(bx), max(bx)
            p.poly([xmin - 14, haut, xmax + 14, haut, xmax + 20, bas - 25, xmax - 6, bas,
                    xmin + 6, bas, xmin - 20, bas - 25],
                   fill=PEAU, stipple="gray25", outline=PEAU_BORD, width=2, smooth=True)
            # pouce
            base_pouce = (xmax + 6, haut + pas * 0.95) if main == 0 else (xmin - 6, haut + pas * 0.95)
            tip_p = self.pouces[main]
            actif_p = doigt == DOIGT_POUCE and main == 1
            p.poly(_capsule(base_pouce, tip_p, pas * 0.38),
                   fill=ACTIF if actif_p else PEAU, stipple="gray50" if actif_p else "gray25",
                   outline=ACTIF_BORD if actif_p else PEAU_BORD, width=2)
            # doigts
            for f in doigts:
                actif = f == doigt
                p.poly(_capsule(bases[f], tuple(self.tips[f]), pas * LARGEURS[f]),
                       fill=ACTIF if actif else PEAU, stipple="gray50" if actif else "gray25",
                       outline=ACTIF_BORD if actif else PEAU_BORD, width=2)
                if noms:
                    p.texte(bases[f][0], bas + 14, text=NOMS_COURTS[f], fill="#cbd5e1",
                            font=("Segoe UI", 8, "bold"))
        if noms:
            sx, sy = kb.pos(" ")
            p.texte(sx, kb.pos(" ")[1] + kb.t * 0.9 + 4, text="Pouces", fill="#cbd5e1",
                    font=("Segoe UI", 8, "bold"))
