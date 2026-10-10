"""Compétitions : championnat, coupe du monde et élimination du dernier.

  CHAMPIONNAT     plusieurs manches avec tous les pilotes ; des points à chaque course.
  COUPE DU MONDE  tableau à élimination : à chaque tour, la moitié basse du classement sort.
  ÉLIMINATION     une seule course : à intervalle régulier, le dernier est éliminé,
                  jusqu'à la fin du temps (ou jusqu'au dernier survivant).

Dans les trois cas tu choisis le nombre de voitures, la durée d'une course et la difficulté.
"""

import random
import time
from datetime import datetime

import stockage
import schema
from config import *
from outils import fmt_duree

FORMATS = {
    "champ": {"nom": "Championnat", "icone": "🏆", "nb": [4, 6, 8, 10, 12, 16, 20], "defaut": 8,
              "desc": "Plusieurs manches avec tous les pilotes. Des points à chaque course : le meilleur total est champion."},
    "cdm": {"nom": "Coupe du monde", "icone": "🌍", "nb": [4, 8, 16, 32], "defaut": 8,
            "desc": "Tableau à élimination. À chaque tour, la moitié basse du classement est éliminée, jusqu'à la finale."},
    "elim": {"nom": "Élimination", "icone": "💀", "nb": [3, 4, 5, 6, 8, 10, 12, 16, 20], "defaut": 8,
             "desc": "Une seule course. À intervalle régulier le dernier est éliminé, jusqu'à la fin du temps."},
}
ORDRE_FORMATS = ["champ", "cdm", "elim"]
MANCHES = [3, 5, 8, 10]
INTERVALLE_MIN = 3.0          # secondes minimum entre deux éliminations

NOMS = ["Axel", "Bruno", "Cléo", "Dario", "Éline", "Farid", "Gaïa", "Hugo", "Ilyes", "Jade", "Kévin",
        "Léa", "Malik", "Nina", "Oscar", "Paola", "Quentin", "Rita", "Samir", "Tess", "Ugo", "Vera",
        "Wassim", "Xena", "Yann", "Zoé", "Adèle", "Boris", "Camille", "Dylan", "Emma", "Félix",
        "Gabin", "Hana", "Ivan", "Jules", "Kim", "Lola", "Marc", "Nora", "Otto", "Pablo"]
PALETTE = ["#2457c5", "#1f9d55", "#e8eaed", "#d946ef", "#0ea5a4", "#f97316",
           "#eab308", "#ef4444", "#8b5cf6", "#14b8a6", "#f43f5e", "#84cc16"]


def ordinal(n):
    return "1er" if n == 1 else f"{n}e"


def nom_tour(m):
    """Nom du tour de la coupe du monde quand il reste m voitures."""
    if m <= 2:
        return "Finale"
    if m <= 4:
        return "Demi-finales"
    if m <= 8:
        return "Quarts de finale"
    if m <= 16:
        return "Huitièmes de finale"
    return "Seizièmes de finale"


def noms_tours(nb):
    noms, m = [], nb
    while True:
        noms.append(nom_tour(m))
        if m <= 2:
            return noms
        m = (m + 1) // 2


def creer_pilotes(nb, diff):
    """nb adversaires, de plus en plus forts (vitesses étalées autour de la difficulté choisie)."""
    bas, _, haut = DIFFICULTES[diff][1]
    vit = [bas * 0.9 + (haut * 1.08 - bas * 0.9) * (i / max(1, nb - 1)) + random.uniform(-2, 2)
           for i in range(nb)]
    random.shuffle(vit)
    noms = random.sample(NOMS, nb)
    return [{"nom": noms[i], "couleur": PALETTE[i % len(PALETTE)], "modele": i % 3, "wpm": vit[i]}
            for i in range(nb)]


class Competition:
    """Une compétition en cours : pilotes, points, éliminés."""

    def __init__(self, fmt, nb, manches, diff, couleur_joueur):
        self.format, self.nb, self.diff = fmt, nb, diff
        self.manches = manches if fmt == "champ" else 1
        self.pilotes = creer_pilotes(nb - 1, diff)
        self.couleurs = {p["nom"]: p["couleur"] for p in self.pilotes}
        self.couleurs["TOI"] = couleur_joueur
        self.pts = {nom: 0 for nom in self.couleurs}
        self.manche = 1
        self.fini = False
        self.joueur_sorti = False
        self.dernier_rang = []
        self.en_lice = list(self.couleurs)
        self.sortis = []
        self.tour_sortie = ""
        self.rang_sortie = None
        self.place = None
        self.resume = ""
        self.bonus_xp = 0
        self.niveau_gagne = None
        self.debloque = []
        self.interval = 0.0
        self.prochaine = 0.0

    # ------------------------------------------------------------ libellés
    def titre_manche(self):
        if self.format == "champ":
            return f"Manche {self.manche}/{self.manches}"
        if self.format == "cdm":
            return nom_tour(len(self.en_lice))
        return "Élimination"

    # ------------------------------------------------------------ course
    def creer_bots(self, jeu):
        bots = []
        for p in self.pilotes:
            if self.format == "cdm" and p["nom"] not in self.en_lice:
                continue
            bots.append(jeu.nouveau_bot(p["nom"], p["couleur"], p["modele"], p["wpm"] + random.uniform(-3, 3)))
        return bots

    def debut_course(self, jeu):
        if self.format == "elim":
            jeu.goal = 10 ** 9              # pas de ligne d'arrivée : on survit jusqu'au bout
            self.interval = max(INTERVALLE_MIN, jeu.duree / self.nb)
            self.prochaine = self.interval
            self.sortis = []

    def maj_course(self, jeu, t):
        """Élimination du dernier. Retourne True si la course vient de se terminer."""
        if self.format != "elim" or t < self.prochaine:
            return False
        self.prochaine += self.interval
        candidats = [(jeu.idx, 1, None)] + [(b.pos, 0, b) for b in jeu.bots]
        dernier = min(candidats, key=lambda c: (c[0], c[1]))      # à égalité, c'est un adversaire qui sort
        if dernier[2] is None:
            jeu.terminer(t, place_force=len(jeu.bots) + 1, fin="elimine")
            return True
        jeu.bots.remove(dernier[2])
        self.sortis.append(dernier[2].nom)
        jeu.notice = (f"💀  {dernier[2].nom} est éliminé !", time.time() + 2.5)
        if not jeu.bots:
            jeu.terminer(t, place_force=1, fin="survivant")
            return True
        return False

    def fin_manche(self, jeu):
        """Appelée à la fin de chaque course (classement des pilotes encore en piste)."""
        rang = [nom for nom, _c, _d in jeu.classement()]
        self.dernier_rang = rang
        if self.format == "champ":
            for i, nom in enumerate(rang):
                self.pts[nom] += self.nb - i
            self.fini = self.manche >= self.manches
        elif self.format == "cdm":
            m = len(rang)
            tour = nom_tour(m)
            if m <= 2:
                self.fini = True
                self.en_lice, self.sortis = rang[:1], self.sortis + rang[1:]
            else:
                garde = (m + 1) // 2
                self.sortis += rang[garde:][::-1]
                self.en_lice = rang[:garde]
            if "TOI" not in self.en_lice or m <= 2:
                self.tour_sortie = tour
                self.rang_sortie = rang.index("TOI") + 1
            self.joueur_sorti = "TOI" not in self.en_lice
            if self.joueur_sorti:
                self.fini = True
        else:
            self.fini = True
            self.dernier_rang = rang

    # ------------------------------------------------------------ résultats
    def lignes_tableau(self):
        """[(rang, nom, couleur, texte de droite)] pour le tableau affiché entre deux courses."""
        if self.format == "champ":
            idx = {nom: i for i, nom in enumerate(self.dernier_rang)}
            ordre = sorted(self.pts, key=lambda n: (-self.pts[n], idx.get(n, 99)))
            return [(i + 1, n, self.couleurs[n], f"{self.pts[n]} pts") for i, n in enumerate(ordre)]
        if self.format == "cdm":
            lignes = []
            for i, n in enumerate(self.dernier_rang):
                if self.fini and not self.joueur_sorti and i == 0 and len(self.dernier_rang) <= 2:
                    droite = "🏆 champion"
                else:
                    droite = "✔ qualifié" if n in self.en_lice else "✖ éliminé"
                lignes.append((i + 1, n, self.couleurs[n], droite))
            return lignes
        ordre = list(self.dernier_rang) + self.sortis[::-1]
        return [(i + 1, n, self.couleurs[n], "survivant" if n in self.dernier_rang else "éliminé")
                for i, n in enumerate(ordre)]

    def conclure(self, jeu):
        """Calcule la place finale, le texte et les XP bonus."""
        if self.format == "champ":
            lignes = self.lignes_tableau()
            self.place = next(r for r, n, _c, _t in lignes if n == "TOI")
            self.bonus_xp = {1: 150, 2: 80, 3: 40}.get(self.place, 0)
            self.resume = (f"Champion avec {self.pts['TOI']} points !" if self.place == 1
                           else f"{ordinal(self.place)} sur {self.nb} avec {self.pts['TOI']} points")
        elif self.format == "cdm":
            self.place = self.rang_sortie or 1
            if not self.joueur_sorti and self.tour_sortie == "Finale" and self.place == 1:
                self.bonus_xp, self.resume = 200, "Champion du monde !"
            elif self.tour_sortie == "Finale":
                self.bonus_xp, self.resume = 100, "Finaliste : tu as été battu en finale"
            else:
                self.bonus_xp = 40 if self.tour_sortie == "Demi-finales" else 0
                self.resume = f"Éliminé en {self.tour_sortie.lower()}"
        else:
            self.place = (jeu.resultat or {}).get("place") or 1
            self.bonus_xp = {1: 120, 2: 60, 3: 30}.get(self.place, 0)
            self.resume = ("Dernier survivant : tu as gagné !" if self.place == 1
                           else f"{ordinal(self.place)} sur {self.nb}")
        ancien = jeu.niveau()
        jeu.data["xp"] += self.bonus_xp
        jeu.data["trophees"].append({"format": self.format, "n": self.nb, "place": self.place,
                                     "date": datetime.now().strftime("%d/%m")})
        jeu.data["trophees"] = jeu.data["trophees"][-30:]
        stockage.sauver(jeu.data)
        nouveau = jeu.niveau()
        self.niveau_gagne = nouveau if nouveau > ancien else None
        self.debloque = stockage.deblocages(ancien, nouveau)


class Champions:
    """Écrans des compétitions : réglages, classement entre deux courses, résultat final."""

    def __init__(self, jeu):
        self.j = jeu
        self.i_fmt = 0
        self.nb = {k: FORMATS[k]["defaut"] for k in FORMATS}
        self.i_manches = 1
        self.diff = "2"

    def cle(self):
        return ORDRE_FORMATS[self.i_fmt]

    # ------------------------------------------------------------ navigation
    def ouvrir(self):
        self.j.etat = "comp_menu"

    def commencer(self):
        j = self.j
        cle = self.cle()
        j.comp = Competition(cle, self.nb[cle], MANCHES[self.i_manches], self.diff,
                             COULEURS[j.data["couleur"]]["hex"])
        j.boss, j.mode = None, "course"
        j.valider_depart()

    def abandon(self, message=True):
        j = self.j
        j.comp = None
        j.part.vider()
        j.mus.arreter()
        j.etat = "comp_menu"
        if message:
            j.notice = ("Compétition abandonnée", time.time() + 3.0)

    def apres_course(self):
        """ENTRÉE sur l'écran de fin d'une course de compétition."""
        c = self.j.comp
        if c.format == "elim":
            self.conclure()
        else:
            self.j.etat = "comp_tableau"

    def conclure(self):
        j, c = self.j, self.j.comp
        c.conclure(j)
        j.part.vider()
        if c.place == 1:
            j.son.victoire()
            j.part.confettis()
        else:
            j.son.defaite()
        j.etat = "comp_fin"

    def touche(self, e):
        k, et = e.keysym, self.j.etat
        if et == "comp_menu":
            self.touche_menu(k)
        elif et == "comp_tableau":
            if k == "Return":
                c = self.j.comp
                if c.fini:
                    self.conclure()
                else:
                    c.manche += 1
                    self.j.demarrer()
            elif k == "Escape":
                self.abandon()
        elif et == "comp_fin":
            if k == "Return":
                self.j.comp = None
                self.commencer()
            elif k == "Escape":
                self.j.comp = None
                self.j.etat = "comp_menu"

    def touche_menu(self, k):
        j, cle = self.j, self.cle()
        if k == "Escape":
            j.etat = "menu"
        elif k in ("Left", "Right"):
            self.i_fmt = (self.i_fmt + (1 if k == "Right" else -1)) % len(ORDRE_FORMATS)
        elif k in ("Up", "Down"):
            opts = FORMATS[cle]["nb"]
            i = opts.index(self.nb[cle]) + (1 if k == "Up" else -1)
            self.nb[cle] = opts[max(0, min(len(opts) - 1, i))]
        elif k.lower() == "n":
            self.i_manches = (self.i_manches + 1) % len(MANCHES)
        elif k.lower() == "d":
            j.duree_suivante()
        elif k.lower() == "u":
            j.ouvrir_saisie()
        elif j.touche_diff(k):
            self.diff = j.touche_diff(k)
        elif k == "Return":
            self.commencer()

    # ------------------------------------------------------------ dessin
    def dessiner(self, now):
        et = self.j.etat
        if et == "comp_menu":
            self.dessiner_menu()
        elif et == "comp_tableau":
            self.dessiner_tableau(now)
        else:
            self.dessiner_fin(now)

    def resume_reglages(self, cle):
        j, nb = self.j, self.nb[cle]
        d = fmt_duree(j.duree_s)
        if cle == "champ":
            return f"{nb} voitures · {MANCHES[self.i_manches]} manches de {d} · 1er = {nb} pts, dernier = 1 pt"
        if cle == "cdm":
            return f"{nb} voitures · " + " → ".join(t.lower() for t in noms_tours(nb)) + f" · {d} par course"
        intervalle = max(INTERVALLE_MIN, j.duree_s / nb)
        texte = f"{nb} voitures · un éliminé toutes les {fmt_duree(round(intervalle))} · course de {d}"
        if j.duree_s / nb < INTERVALLE_MIN:
            texte += "  (durée courte : il restera plusieurs survivants)"
        return texte

    def dessiner_menu(self):
        j, p = self.j, self.j.p
        cle = self.cle()
        j.titre_fx(W // 2, 38, "COMPÉTITIONS", 30)
        p.texte(W // 2, 72, text="Choisis un format, le nombre de voitures et la durée des courses", fill=GRIS,
                font=("Segoe UI", 11))
        for i, k in enumerate(ORDRE_FORMATS):
            f = FORMATS[k]
            x0 = 40 + i * 285
            x1, y0, y1 = x0 + 250, 92, 268
            actif = i == self.i_fmt
            survol = x0 <= j.souris[0] <= x1 and y0 <= j.souris[1] <= y1
            p.rect(x0, y0, x1, y1, r=16, fill=CARTE_HAUT if actif else CARTE,
                   outline=ACCENT if actif else (ACCENT2 if survol else BORD), width=3 if actif else 2)
            p.texte((x0 + x1) / 2, y0 + 36, text=f["icone"], font=("Segoe UI Emoji", 28))
            p.texte((x0 + x1) / 2, y0 + 78, text=f["nom"], fill=ACCENT if actif else BLANC,
                    font=("Segoe UI", 15, "bold"))
            p.texte((x0 + x1) / 2, y0 + 128, text=f["desc"], fill="#cbd5e1", font=("Segoe UI", 10),
                    width=214, justify="center")
            j.zone(x0, y0, x1, y1, lambda i=i: setattr(self, "i_fmt", i))

        y = 302
        opts_nb = [(f"{n} voitures", n) for n in FORMATS[cle]["nb"]]
        j.liste("c_nb", 128, y, 200, 34, f"Voitures : {self.nb[cle]}", opts_nb, self.nb[cle],
                lambda v: self.nb.__setitem__(cle, v), 11)
        if cle == "champ":
            j.liste("c_man", 343, y, 200, 34, f"Manches : {MANCHES[self.i_manches]}",
                    [(f"{m} manches", i) for i, m in enumerate(MANCHES)], self.i_manches,
                    lambda v: setattr(self, "i_manches", v), 11)
        else:
            j.bouton(243, y - 17, 443, y + 17, "Manches : automatiques" if cle == "cdm" else "Une seule course",
                     None, taille=10, desactive=True)
        j.liste_duree("c_duree", 558, y, 200, 34, 11, prefixe="Course")
        j.liste("c_diff", 773, y, 200, 34, f"Niveau : {DIFFICULTES[self.diff][0]}",
                [(nom, c) for c, (nom, _v) in DIFFICULTES.items()], self.diff,
                lambda v: setattr(self, "diff", v), 11)

        p.texte(W // 2, 346, text=self.resume_reglages(cle), fill=JAUNE, font=("Segoe UI", 11, "bold"))
        j.bouton(270, 372, 630, 428, "COMMENCER  (ENTRÉE)", self.commencer, fond="#10b981", fg=BLANC,
                 taille=17, r=18)
        troph = j.data["trophees"][-3:][::-1]
        if troph:
            p.texte(W // 2, 458, text="Derniers résultats", fill=GRIS, font=("Segoe UI", 10, "bold"))
            for i, t in enumerate(troph):
                nom = FORMATS.get(t["format"], {"nom": t["format"], "icone": "🏁"})
                p.texte(W // 2, 478 + i * 18, text=f"{nom['icone']}  {nom['nom']} · {t['n']} voitures · "
                        f"{ordinal(t.get('place', 0)) if t.get('place') else '—'}  ({t.get('date', '')})",
                        fill="#cbd5e1", font=("Segoe UI", 10))
        j.bouton(24, 524, 184, 550, "◀  Retour (ÉCHAP)", lambda: j.simuler("Escape"), taille=10, r=10)
        p.texte(W - 24, 537, text="← → format   ↑ ↓ voitures   N manches   D / U durée   1 2 3 niveau",
                anchor="e", fill=GRIS, font=("Segoe UI", 9))

    def dessiner_tableau(self, now):
        j, p, c = self.j, self.j.p, self.j.comp
        # coupe du monde : le classement est celui du tour qui vient d'être couru (pas du suivant)
        tour = nom_tour(len(c.dernier_rang)) if c.format == "cdm" and c.dernier_rang else c.titre_manche()
        j.titre_fx(W // 2, 36, f"CLASSEMENT · {tour.upper()}", 24)
        lignes = c.lignes_tableau()
        moi = next((l for l in lignes if l[1] == "TOI"), None)
        if c.format == "champ":
            sous = f"{c.nb} pilotes · {c.manches - c.manche} manche(s) restante(s)"
        elif c.format == "cdm":
            if c.joueur_sorti:
                sous = f"Tu es éliminé en {nom_tour(len(c.dernier_rang)).lower()}"
            elif c.fini:
                sous = "Bravo, tu es champion du monde !"
            else:
                m = len(c.en_lice)
                sous = "Tu es qualifié pour " + ("la finale" if m <= 2 else "les " + nom_tour(m).lower())
        else:
            sous = ""
        p.texte(W // 2, 66, text=sous, fill=VERT if "qualifié" in sous or "Bravo" in sous else GRIS,
                font=("Segoe UI", 12, "bold"))

        # schéma de ta position (coupe du monde : tableau jusqu'au trophée ; championnat : route des manches)
        if c.format == "cdm":
            p.rect(30, 80, W - 30, 262, r=16, fill=CARTE, outline=BORD, width=2)
            schema.dessiner_schema_cdm(p, c, 40, 84, W - 40, 258, now)
            haut, pas, nmax = 272, 28, 6
        elif c.format == "champ":
            p.rect(30, 80, W - 30, 174, r=16, fill=CARTE, outline=BORD, width=2)
            schema.dessiner_schema_champ(p, c, 40, 84, W - 40, 170, now,
                                         moi[0] if moi else c.nb, c.pts.get("TOI", 0))
            haut, pas, nmax = 184, 27, 8
        else:
            haut, pas, nmax = 86, 33, 10

        visibles = lignes[:nmax]
        if moi and moi not in visibles:
            visibles = visibles[:nmax - 1] + [moi]
        p.rect(130, haut, 770, haut + pas * len(visibles) + 14, r=16, fill=CARTE, outline=BORD, width=2)
        gros = 13 if pas >= 30 else 12
        for i, (rang, nom, col, droite) in enumerate(visibles):
            y = haut + 7 + i * pas + pas / 2
            if nom == "TOI":
                p.rect(138, y - pas / 2 + 1.5, 762, y + pas / 2 - 1.5, r=10, fill=CARTE_HAUT, outline=ACCENT, width=2)
            p.texte(170, y, text=str(rang), fill=JAUNE if rang <= 3 else GRIS, font=("Segoe UI", gros, "bold"))
            p.rect(205, y - 8, 221, y + 8, r=4, fill=col)
            p.texte(236, y, text=nom, anchor="w", fill=ACCENT if nom == "TOI" else BLANC,
                    font=("Segoe UI", gros, "bold" if nom == "TOI" else "normal"))
            vert = ("✔" in droite or "🏆" in droite or "survivant" in droite)
            p.texte(745, y, text=droite, anchor="e", fill=(VERT if vert else (ROUGE if "✖" in droite or "éliminé" in droite else BLANC)),
                    font=("Segoe UI", 12, "bold"))
        suite = "VOIR LE RÉSULTAT FINAL  (ENTRÉE)" if c.fini else "MANCHE SUIVANTE  (ENTRÉE)"
        j.bouton(270, 484, 630, 530, suite, lambda: j.simuler("Return"), fond="#10b981", fg=BLANC, taille=15, r=16)
        j.bouton(24, 500, 190, 528, "Abandonner (ÉCHAP)", lambda: j.simuler("Escape"), taille=10, r=10)

    def dessiner_fin(self, now):
        j, p, c = self.j, self.j.p, self.j.comp
        podium = c.place in (1, 2, 3)
        couleur = schema.MEDAILLES[c.place][1] if podium else BORD
        p.rect(110, 40, 790, 520, r=24, fill=CARTE, outline=couleur, width=3)
        gagne = c.place == 1 or (c.format == "cdm" and not c.joueur_sorti)
        titre = {"champ": "🏆  CHAMPION !", "cdm": "🌍  CHAMPION DU MONDE !", "elim": "🏁  DERNIER SURVIVANT !"}[c.format] \
            if c.place == 1 else f"{FORMATS[c.format]['icone']}  {ordinal(c.place)} place"
        p.texte(W // 2 + 2, 82, text=titre, fill="#000000", font=("Segoe UI", 28, "bold"))
        p.texte(W // 2, 80, text=titre, fill=JAUNE if gagne else BLANC, font=("Segoe UI", 28, "bold"))

        if podium:
            # position + message, puis trophée (1re place) ou médaille (2e, 3e)
            texte = schema.phrase_podium(c.place)
            demi = 22 + len(texte) * 5.0
            p.rect(W // 2 - demi, 114, W // 2 + demi, 148, r=16, fill="#0a1030", outline=couleur, width=2)
            p.texte(W // 2, 131, text=texte, fill=couleur, font=("Segoe UI", 13, "bold"))
            y_res, y_sub = 172, 194
            haut = 214 if c.format == "cdm" else 232
            schema.dessiner_recompense(p, 215, 305, 1.15 if c.place == 1 else 1.3, c.place, now)
            p.texte(215, 392, text=schema.MEDAILLES[c.place][0], fill=couleur, font=("Segoe UI", 12, "bold"))
            gauche, droite, centre = 310, 770, 540
        else:
            y_res, y_sub = 126, 156
            haut = 190
            gauche, droite, centre = 260, 640, 450
        p.texte(W // 2, y_res, text=c.resume, fill="#e2e8f0", font=("Segoe UI", 13, "bold"))
        p.texte(W // 2, y_sub, text=f"{FORMATS[c.format]['nom']} · {c.nb} voitures", fill=GRIS,
                font=("Segoe UI", 11))

        if c.format == "cdm":
            # le tableau complet jusqu'au trophée, avec ta position finale
            g = gauche if podium else 130
            schema.dessiner_schema_cdm(p, c, g, haut, droite, haut + 170, now)
            y = haut + 190
        else:
            for i, (rang, nom, col, texte_d) in enumerate(c.lignes_tableau()[:5]):
                y = haut + i * 30
                if nom == "TOI":
                    p.rect(gauche, y - 13, droite, y + 13, r=9, fill=CARTE_HAUT, outline=ACCENT, width=2)
                p.texte(gauche + 30, y, text=str(rang), fill=JAUNE if rang <= 3 else GRIS, font=("Segoe UI", 12, "bold"))
                p.rect(gauche + 56, y - 7, gauche + 70, y + 7, r=3, fill=col)
                p.texte(gauche + 84, y, text=nom, anchor="w", fill=ACCENT if nom == "TOI" else BLANC,
                        font=("Segoe UI", 12, "bold"))
                p.texte(droite - 15, y, text=texte_d, anchor="e", fill=GRIS, font=("Segoe UI", 11))
            y = haut + 5 * 30 + 4
        if c.bonus_xp:
            p.texte(centre, y, text=f"+{c.bonus_xp} XP de bonus", fill=JAUNE, font=("Segoe UI", 15, "bold"))
            y += 28
        if c.niveau_gagne:
            msg = f"NIVEAU {c.niveau_gagne} !"
            if c.debloque:
                msg += "   Débloqué : " + ", ".join(c.debloque)
            p.texte(centre, y, text=msg, fill=VERT, font=("Segoe UI", 12, "bold"), width=520, justify="center")
        j.part.dessiner(p)
        j.bouton(190, 450, 440, 496, "REJOUER  (ENTRÉE)", lambda: j.simuler("Return"), fond="#10b981", fg=BLANC,
                 taille=14, r=16)
        j.bouton(460, 450, 710, 496, "COMPÉTITIONS  (ÉCHAP)", lambda: j.simuler("Escape"), taille=14, r=16)
