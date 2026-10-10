"""Scène 3D de la course : ciel, montagnes, route en perspective, décor, voitures."""

import math
import random
import zlib

import modeles
from config import (DEMI_ROUTE, HAUT_PANNEAU, H, PISTES, W)
from moteur3d import Camera, Eclairage, melanger, rendre

SEG = 4.0                                  # longueur d'une bande de route (m)
DIST_MAX = {1: 75.0, 2: 115.0, 3: 150.0}   # distance d'affichage selon la qualité
ESPACEMENT = {1: 26.0, 2: 20.0, 3: 16.0}   # distance entre deux objets du décor
CAM_Y, CAM_Z = 3.2, -11.0                  # hauteur et recul de la caméra


def deformer(r):
    """Compresse les grandes distances pour que tous les pilotes restent visibles.

    r = distance (en mètres) devant le joueur ; renvoie la distance affichée.
    """
    if r < 0:
        return -3.5 * (1.0 - math.exp(r / 14.0))
    if r < 30.0:
        return r
    return 30.0 + 30.0 * (1.0 - math.exp(-(r - 30.0) / 40.0))


class Scene3D:
    def __init__(self, peintre):
        self.p = peintre
        self.cam = Camera(x=0.0, y=CAM_Y, z=CAM_Z, pitch=0.12, focale=520.0, cx=W / 2, cy=250.0)
        self.ancre_joueur = (W / 2, 380.0)
        self._ecl = {}
        self._decor = {}

    def ecl(self, piste):
        if piste["nom"] not in self._ecl:
            self._ecl[piste["nom"]] = Eclairage(piste)
        return self._ecl[piste["nom"]]

    # ------------------------------------------------------------ fond fixe
    def fond_statique(self, piste):
        p, cam = self.p, self.cam
        hy = cam.horizon()
        haut, bas = piste["ciel"]
        graine = zlib.crc32(piste["nom"].encode())
        rnd = random.Random(graine)

        n = 26
        for i in range(n):
            t = (i / (n - 1)) ** 1.5
            p.rect(0, hy * i / n, W, hy * (i + 1) / n + 1, fill=melanger(haut, bas, t))

        if piste.get("etoiles"):
            for _ in range(70):
                x, y = rnd.randint(0, W), rnd.randint(4, int(hy) - 70)
                r = rnd.choice((1, 1, 2))
                p.oval(x, y, x + r, y + r, fill="#e8eeff")
        if piste.get("soleil"):
            col, xr = piste["soleil"]
            cx, cy = W * xr, hy - 78
            for r, t in ((92, 0.07), (62, 0.14), (42, 0.28)):
                p.oval(cx - r, cy - r, cx + r, cy + r, fill=melanger(bas, col, t))
            p.oval(cx - 20, cy - 20, cx + 20, cy + 20, fill=col)
        if piste.get("lune"):
            cx, cy = W * piste["lune"], hy - 95
            for r, t in ((52, 0.08), (36, 0.2)):
                p.oval(cx - r, cy - r, cx + r, cy + r, fill=melanger(bas, "#dfe8ff", t))
            p.oval(cx - 20, cy - 20, cx + 20, cy + 20, fill="#f2f6ff")

        # relief ou immeubles lointains, du plus loin au plus proche
        ville = piste["nom"] == "Ville"
        for couche, col in enumerate(piste["montagnes"]):
            base = (98, 64, 34)[couche]
            amp = (58, 38, 22)[couche]
            phase = rnd.uniform(0, 6)
            freq = (0.011, 0.017, 0.026)[couche]
            if ville:
                x = 0
                while x < W:
                    w = rnd.randint(28, 62)
                    h = base * 0.55 + rnd.uniform(0, amp * 1.6)
                    p.rect(x, hy - h, x + w, hy + 2, fill=col)
                    x += w
            else:
                pts = [0, hy + 2]
                x = 0
                while x <= W + 20:
                    h = base + amp * (0.5 + 0.5 * math.sin(x * freq + phase)
                                      + 0.25 * math.sin(x * freq * 2.7 + phase * 1.7))
                    h *= rnd.uniform(0.94, 1.04)
                    pts += [x, hy - h]
                    x += 20
                pts += [W, hy + 2]
                p.poly(pts, fill=col)

        # sol de base + voile de brume à l'horizon
        p.rect(0, hy, W, HAUT_PANNEAU, fill=piste["herbe"][0])
        for i in range(8):
            t = 0.75 * (1 - i / 8)
            p.rect(0, hy + i * 3, W, hy + i * 3 + 3, fill=melanger(piste["herbe"][0], piste["brume"], t))

    # ------------------------------------------------------------ utilitaires
    def _info_decor(self, piste, i, cote):
        cle = (piste["nom"], i, cote)
        if cle not in self._decor:
            rnd = random.Random((i * 73856093) ^ (cote * 19349663) ^ zlib.crc32(piste["nom"].encode()))
            genre = rnd.choice(piste["deco"])
            if genre == "immeuble":
                genre = "immeuble%d" % rnd.randint(0, 3)
                dx = rnd.uniform(14.0, 20.0)
            elif genre == "lampadaire":
                dx = 8.6
            else:
                dx = rnd.uniform(10.0, 19.0)
            if len(self._decor) > 600:          # (vidé avant l'ajout : les très longues courses y passent souvent)
                self._decor.clear()
            self._decor[cle] = (genre, dx, rnd.uniform(0.85, 1.3), rnd.uniform(0, 6.28),
                                rnd.uniform(-4.0, 4.0))
        return self._decor[cle]

    # ------------------------------------------------------------ dessin
    def dessiner(self, piste, qualite, z_joueur, voitures, z_arrivee, temps, wpm,
                 secousse=(0.0, 0.0), feux_vifs=True):
        p, cam = self.p, self.cam
        ecl = self.ecl(piste)
        dist_max = DIST_MAX[qualite]
        cam.x = voitures[0]["x"] * 0.6 if voitures else 0.0
        cam.x += secousse[0]
        cam.y = CAM_Y + secousse[1]
        cam.z = CAM_Z
        hy = cam.horizon()

        if not piste.get("nuit") and not piste.get("etoiles"):
            self._nuages(piste, temps, hy, qualite)
        self._sol(piste, ecl, z_joueur, dist_max)
        self._lignes(ecl, z_joueur, z_arrivee, dist_max)

        objets = []      # (profondeur, polygones) pour le tri global
        # décor le long de la route
        esp = ESPACEMENT[qualite]
        i0 = int(math.floor((z_joueur - 8) / esp))
        i1 = int(math.ceil((z_joueur + dist_max) / esp))
        nuit = bool(piste.get("nuit"))
        for i in range(i0, i1 + 1):
            for cote in (-1, 1):
                genre, dx, ech, rot, dz = self._info_decor(piste, i, cote)
                rel = i * esp + dz - z_joueur
                if rel < -5 or rel > dist_max:
                    continue
                zv = deformer(rel)
                x = cote * dx
                yaw = rot
                if genre.startswith("immeuble"):
                    x = cote * (dx + 6)
                    yaw = math.pi if cote > 0 else 0.0
                    ech = 1.0
                elif genre == "lampadaire":
                    yaw = math.pi if cote > 0 else 0.0
                    ech = 1.0
                maillage = modeles.decor(genre, nuit, qualite >= 2)
                polys = rendre(cam, maillage, (x, 0.0, zv), ecl, yaw=yaw, echelle=ech)
                if not polys:
                    continue
                if genre == "lampadaire":
                    tete = cam.proj(x - cote * 2.0, 6.2, zv)
                    if tete:
                        r = max(4.0, 300.0 / tete[2])
                        p.oval(tete[0] - r, tete[1] - r, tete[0] + r, tete[1] + r,
                               fill=melanger(piste["brume"], "#ffe9a8", 0.35))
                objets.append((zv, polys))

        # portique d'arrivée
        rel = z_arrivee - z_joueur
        if -4 < rel < dist_max:
            zv = deformer(rel)
            objets.append((zv, rendre(cam, modeles.arche(), (0.0, 0.0, zv), ecl)))

        # voitures (ombre au sol d'abord)
        ancre = None
        ombre_col = melanger(piste["route"][0], "#000000", 0.5)
        for v in voitures:
            rel = v["z"] - z_joueur
            if rel > dist_max or rel < -60:
                continue
            zv = deformer(rel)
            self._ombre(v["x"], zv, ombre_col)
            y = 0.0
            if v.get("joueur"):
                y = 0.014 * math.sin(temps * 26) * min(1.0, wpm / 60.0)
            feux = "#ff3b3b" if (feux_vifs or not v.get("joueur")) else "#8c1414"
            polys = rendre(cam, modeles.voiture(v["modele"]), (v["x"], y, zv), ecl,
                           couleur_carro=v["couleur"], feux=feux)
            objets.append((zv, polys))
            if v.get("joueur"):
                a = cam.proj(v["x"], 0.45, zv - 2.2)
                if a:
                    ancre = (a[0], a[1])

        objets.sort(key=lambda o: -o[0])
        for _, polys in objets:
            for _, coords, col in polys:
                p.poly(coords, fill=col, outline=col)

        # noms au-dessus des voitures
        loin, derriere = (95, -60) if len(voitures) <= 7 else (45, -18)     # beaucoup de voitures : moins d'étiquettes
        for v in voitures:
            rel = v["z"] - z_joueur
            if rel > loin or rel < derriere:
                continue
            a = cam.proj(v["x"], 2.15 if v["modele"] != 2 else 2.4, deformer(rel))
            if not a:
                continue
            if v.get("joueur"):
                p.poly([a[0] - 7, a[1] - 18, a[0] + 7, a[1] - 18, a[0], a[1] - 8], fill="#ffffff")
                p.texte(a[0], a[1] - 28, text="TOI", fill="#ffffff", font=("Segoe UI", 10, "bold"))
            else:
                p.texte(a[0], a[1] - 12, text=v["nom"], fill="#ffffff", font=("Segoe UI", 8, "bold"))

        self._lignes_vitesse(wpm, temps, hy)
        if ancre:
            self.ancre_joueur = ancre

    def _nuages(self, piste, temps, hy, qualite=2):
        p = self.p
        graine = zlib.crc32(piste["nom"].encode())
        rnd = random.Random(graine + 5)
        for k in range((3, 5, 6)[qualite - 1]):
            x = (rnd.uniform(0, W + 300) + temps * (4 + k)) % (W + 300) - 150
            y = rnd.uniform(35, hy - 90)
            echelle = rnd.uniform(0.8, 1.5)
            col = melanger(piste["ciel"][1], "#ffffff", 0.6)      # couleur unie : le stipple Tk est très lent sous Windows
            for dx, dy, r in ((0, 0, 26), (28, 6, 20), (-26, 8, 18), (10, -10, 18)):
                p.oval(x + (dx - r) * echelle, y + (dy - r * 0.6) * echelle,
                       x + (dx + r) * echelle, y + (dy + r * 0.6) * echelle,
                       fill=col)

    def _sol(self, piste, ecl, z_joueur, dist_max):
        p, cam = self.p, self.cam
        k0 = int(math.floor((z_joueur - 6.0) / SEG))
        k1 = int(math.ceil((z_joueur + dist_max) / SEG))
        fronts = []
        for k in range(k0, k1 + 1):
            zv = deformer(k * SEG - z_joueur)
            rz = zv - cam.z
            ry = -cam.y
            zc = -ry * cam.sp + rz * cam.cp
            if zc < 0.6:
                continue
            f = cam.focale / zc
            ys = cam.cy - (ry * cam.cp + rz * cam.sp) * f
            yh = cam.cy - ((0.6 - cam.y) * cam.cp + rz * cam.sp) * f      # haut de la glissière
            fronts.append((k, zc, ys, f, yh))

        def sx(x, f):
            return cam.cx + (x - cam.x) * f

        herbe, route = piste["herbe"], piste["route"]
        R = DEMI_ROUTE
        for i in range(len(fronts) - 2, -1, -1):     # du plus loin au plus proche
            k, zn, yn, fn, hn = fronts[i]
            _, zf, yf, ff, hf = fronts[i + 1]
            if yn - yf < 0.4 or yn < 0 or yf > HAUT_PANNEAU:
                continue
            par = k & 1
            zm = (zn + zf) / 2
            fog = ecl.brumer
            petit = (yn - yf) < 2.0
            yn = yn + 1.2          # léger recouvrement : pas de fines lignes entre les bandes
            hn = hn + 1.2

            p.rect(0, yf, W, yn + 1, fill=fog(herbe[par], zm))
            col = fog(route[par], zm)
            p.poly([sx(-R, fn), yn, sx(R, fn), yn, sx(R, ff), yf, sx(-R, ff), yf], fill=col)
            if petit:              # très loin : route et herbe suffisent (moins de polygones)
                continue
            col = fog("#c0262d" if par else "#f1f1f1", zm)
            p.poly([sx(R, fn), yn, sx(R + 0.9, fn), yn, sx(R + 0.9, ff), yf, sx(R, ff), yf], fill=col)
            p.poly([sx(-R - 0.9, fn), yn, sx(-R, fn), yn, sx(-R, ff), yf, sx(-R - 0.9, ff), yf], fill=col)
            if par == 0:
                col = fog("#e9e9e4", zm)
                for x in (-3.0, 0.0, 3.0):
                    p.poly([sx(x - 0.09, fn), yn, sx(x + 0.09, fn), yn,
                            sx(x + 0.09, ff), yf, sx(x - 0.09, ff), yf], fill=col)
            # glissières
            gx = R + 1.7
            clair = fog("#dfe3e8" if par else "#c9302c", zm)
            sombre = fog("#9aa1a9" if par else "#8e1f1d", zm)
            p.poly([sx(gx, fn), yn, sx(gx, fn), hn, sx(gx, ff), hf, sx(gx, ff), yf], fill=sombre)
            p.poly([sx(-gx, fn), yn, sx(-gx, fn), hn, sx(-gx, ff), hf, sx(-gx, ff), yf], fill=clair)

    def _lignes(self, ecl, z_joueur, z_arrivee, dist_max):
        """Ligne de départ et ligne d'arrivée en damier sur la route."""
        p, cam = self.p, self.cam
        for z in (0.0, z_arrivee):
            rel = z - z_joueur
            if rel < -6 or rel > dist_max:
                continue
            zv = deformer(rel)
            for r in range(2):
                for c in range(12):
                    if (r + c) % 2:
                        continue
                    x0 = -DEMI_ROUTE + c
                    pts = [cam.proj(x0, 0.01, zv + r * 0.7), cam.proj(x0 + 1, 0.01, zv + r * 0.7),
                           cam.proj(x0 + 1, 0.01, zv + (r + 1) * 0.7), cam.proj(x0, 0.01, zv + (r + 1) * 0.7)]
                    if None in pts:
                        continue
                    col = ecl.brumer("#f2f2f2", pts[0][2])
                    p.poly([v for q in pts for v in q[:2]], fill=col)

    def _ombre(self, x, zv, couleur="#222222"):
        cam = self.cam
        pts = []
        for j in range(12):
            a = 2 * math.pi * j / 12
            q = cam.proj(x + 1.15 * math.cos(a), 0.02, zv + 2.3 * math.sin(a))
            if q is None:
                return
            pts += [q[0], q[1]]
        self.p.poly(pts, fill=couleur)

    def _lignes_vitesse(self, wpm, temps, hy):
        n = int(min(wpm, 150) / 14)
        if n <= 0:
            return
        p = self.p
        for i in range(n):
            ang = (i * 2.399963) % 1.0                 # répartition régulière
            a = math.radians(-32 + 60 * ang) if i % 2 == 0 else math.radians(148 + 60 * ang)
            ph = (temps * (1.2 + wpm / 90.0) + i * 0.37) % 1.0
            r0 = 130 + ph * 330
            r1 = r0 + 30 + ph * 90
            x0, y0 = W / 2 + r0 * math.cos(a), hy + 20 + r0 * math.sin(a)
            x1, y1 = W / 2 + r1 * math.cos(a), hy + 20 + r1 * math.sin(a)
            if y1 > HAUT_PANNEAU - 6 or y0 > HAUT_PANNEAU - 6:
                continue
            p.ligne(x0, y0, x1, y1, fill="#eef6ff", width=1)

    # ------------------------------------------------------------ garage
    def apercu_voiture(self, modele, couleur, piste, angle, x0, y0, x1, y1):
        """Voiture qui tourne sur une plateforme (aperçu du garage)."""
        p = self.p
        ecl = self.ecl(piste)
        haut, bas = piste["ciel"]
        hy = y0 + (y1 - y0) * 0.5
        n = 10
        for i in range(n):
            p.rect(x0, y0 + (hy - y0) * i / n, x1, y0 + (hy - y0) * (i + 1) / n + 1,
                   fill=melanger(haut, bas, (i / (n - 1)) ** 1.4))
        p.rect(x0, hy, x1, y1, fill=piste["herbe"][0])
        cam = Camera(x=0.0, y=1.7, z=-9.5, pitch=0.10, focale=680.0,
                     cx=(x0 + x1) / 2, cy=(y0 + y1) / 2)
        for maillage, kw in ((modeles.plateforme(), {}),
                             (modeles.voiture(modele), {"couleur_carro": couleur, "yaw": angle})):
            for _, coords, col in rendre(cam, maillage, (0.0, 0.0, 0.0), ecl, **kw):
                p.poly(coords, fill=col, outline=col)
