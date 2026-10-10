"""Mode théorique : apprendre à taper sans regarder, sur un clavier virtuel.

Le clavier est affiché avec les touches MASQUÉES : une touche n'affiche sa lettre
que lorsque tu l'as tapée. Des mains semi-transparentes montrent la bonne technique.
Niveaux : rangée de base -> voyelles -> consonnes -> mots français -> mots anglais -> défi.
"""

import random
import time

import stockage
from clavier import (JAUNE_FLASH, LAYOUTS, NOMS_DOIGTS, ORDRE, Clavier, Mains,
                     dessiner_clavier, detecter_clavier)
from config import *

KB_X, KB_Y, KB_PAS = 138, 175, 58

NIVEAUX = [
    {"nom": "La rangée de base", "court": "Position de départ : les 8 doigts sur la rangée du milieu",
     "desc": "Ta position de départ : les 8 doigts reposent sur la rangée du milieu. "
             "C'est de là que tes doigts partent et reviennent, toujours."},
    {"nom": "Les voyelles", "court": "A, E, I, O, U, Y : les lettres les plus fréquentes",
     "desc": "A, E, I, O, U, Y : les lettres les plus fréquentes. Elles sont réparties sur "
             "plusieurs rangées : utilise toujours le doigt de leur colonne."},
    {"nom": "Les consonnes", "court": "Toutes les autres lettres de l'alphabet",
     "desc": "Toutes les autres lettres. Garde le rythme régulier et la précision "
             "avant la vitesse : la vitesse viendra toute seule."},
    {"nom": "Mots français", "court": "De vrais mots français, sans regarder le clavier",
     "desc": "Place aux vrais mots ! Tape sans regarder ton clavier : tes yeux restent sur le texte."},
    {"nom": "Mots anglais", "court": "Des mots anglais, utiles pour programmer",
     "desc": "Même technique avec des mots anglais : utile pour programmer et naviguer sur Internet."},
    {"nom": "Défi final", "court": "Mélange de français et d'anglais pour finir",
     "desc": "Un mélange de mots français et anglais. Réussis-le et tu es prêt pour la course !"},
]


def conseils_niveau(niv, kb):
    g = kb.rangees[1][3].upper()
    d = kb.rangees[1][6].upper()
    if niv == 1:
        return [f"Pose les index sur les repères (petites barres) : touches {g} et {d}. Les autres doigts suivent.",
                "Poignets droits, doigts légèrement courbés, pouces au-dessus de la barre d'espace.",
                "Regarde l'écran, jamais tes mains : après chaque lettre, ton doigt revient à sa place de départ."]
    if niv == 2:
        return ["Chaque doigt a sa colonne : l'index gauche couvre 2 colonnes, l'index droit aussi.",
                "Si tu hésites, la touche s'éclaire en jaune après 2 erreurs : mémorise sa place.",
                "Les touches se dévoilent quand tu les tapes : ton clavier se « remplit » peu à peu."]
    if niv == 3:
        return ["Précision d'abord : une erreur te bloque jusqu'à ce que tu tapes la bonne touche.",
                "Tape sans à-coups : un rythme régulier vaut mieux que des rafales.",
                "Le guide des doigts (touche F1) peut être coupé quand tu te sens à l'aise."]
    if niv in (4, 5):
        return ["Tape des mots entiers, d'un seul souffle, puis la barre d'espace avec le pouce.",
                "Ne regarde pas le clavier, même si tu te trompes : relis simplement l'écran.",
                f"Il faut {SEUIL_THEORIE} % de précision pour réussir le niveau."]
    return ["Dernier niveau : mélange de mots français et anglais.",
            "Respire, garde ton rythme et ne regarde pas tes mains.",
            f"Réussis-le ({SEUIL_THEORIE} % de précision) et passe à la course avec Tab !"]


def generer(niv, kb):
    """Construit le texte à taper pour un niveau."""
    lettres = kb.lettres()
    voyelles = [c for c in "aeiouy" if c in lettres]
    consonnes = sorted(lettres - set(voyelles))
    if niv == 1:
        base = kb.rangees[1]
        dispo, groupes = [], []
        for etape in [(3, 6), (2, 7), (1, 8), (0, 9), (4, 5)]:
            nouveaux = [base[c] for c in etape]
            dispo += nouveaux
            for _ in range(3):
                g = [random.choice(nouveaux)] + [random.choice(dispo) for _ in range(3)]
                random.shuffle(g)
                groupes.append("".join(g))
        return " ".join(groupes)
    if niv == 2:
        return " ".join("".join(random.choice(voyelles) for _ in range(4)) for _ in range(14))
    if niv == 3:
        return " ".join("".join(random.choice(consonnes) for _ in range(4)) for _ in range(15))
    fr, en = MOTS["fr"][1], MOTS["en"][1]
    if niv == 4:
        mots = random.sample(fr, 22)
    elif niv == 5:
        mots = random.sample(en, 22)
    else:
        mots = random.sample(fr, 15) + random.sample(en, 15)
        random.shuffle(mots)
    return " ".join(mots)


def lettres_nouvelles(niv, kb):
    lettres = kb.lettres()
    voyelles = {c for c in "aeiouy" if c in lettres}
    if niv == 1:
        return set(kb.rangees[1])
    if niv == 2:
        return voyelles
    if niv == 3:
        return lettres - voyelles
    return set()


class Theorie:
    def __init__(self, jeu):
        self.j = jeu
        self.sel = 0
        self.niv = 1
        self.message = ""
        self.kb = None
        self.mains = None
        self.layout_prepare = None
        self.detecte = None
        self.cible = ""
        self.idx = self.erreurs = 0
        self.reveles = set()
        self.flashs = {}
        self.t_debut = None
        self.erreurs_consec = 0
        self.indice_jusqu = 0.0
        self.lettres = {}
        self.res = {}

    # ------------------------------------------------------------ utilitaires
    def layout(self):
        return self.j.data["clavier"]

    def prog(self):
        return stockage.progression_theorie(self.j.data, self.layout())

    def preparer(self):
        if self.layout_prepare != self.layout():
            self.kb = Clavier(self.layout(), KB_X, KB_Y, KB_PAS)
            self.mains = Mains(self.kb)
            self.layout_prepare = self.layout()

    def detection(self):
        if self.detecte is None:
            self.detecte = detecter_clavier()
        return self.detecte

    def ouvrir(self):
        if self.j.data["clavier"]:
            self.j.etat = "th_niveaux"
            self.sel = min(self.prog()["debloque"], NB_NIVEAUX_THEORIE) - 1
        else:
            self.j.etat = "th_clavier"
            self.sel = 0

    # ------------------------------------------------------------ clavier
    def touche(self, e):
        k = e.keysym
        et = self.j.etat
        if et == "th_jeu":
            self.touche_jeu(e)
            return
        if k == "Tab":
            self.j.aller_pratique()
            return
        if et == "th_clavier":
            self.touche_clavier(k)
        elif et == "th_niveaux":
            self.touche_niveaux(k)
        elif et == "th_intro":
            if k == "Return":
                self.commencer()
            elif k == "Escape":
                self.j.etat = "th_niveaux"
        elif et == "th_fin":
            self.touche_fin(k)

    def touche_clavier(self, k):
        n = len(ORDRE) + 1
        if k in ("Up", "Down"):
            self.sel = (self.sel + (1 if k == "Down" else -1)) % n
        elif k == "Return":
            if self.sel == 0:
                lid, expl = self.detection()
                self.message = f"Clavier détecté : {LAYOUTS[lid]['nom']}  ({expl})"
            else:
                lid = ORDRE[self.sel - 1]
                self.message = f"Clavier choisi : {LAYOUTS[lid]['nom']}"
            self.j.data["clavier"] = lid
            stockage.sauver(self.j.data)
            self.layout_prepare = None
            self.j.etat = "th_niveaux"
            self.sel = min(self.prog()["debloque"], NB_NIVEAUX_THEORIE) - 1
        elif k == "Escape":
            if self.j.data["clavier"]:
                self.j.etat = "th_niveaux"
            else:
                self.j.etat = "accueil"

    def touche_niveaux(self, k):
        if k in ("Up", "Down"):
            self.sel = (self.sel + (1 if k == "Down" else -1)) % NB_NIVEAUX_THEORIE
            self.message = ""
        elif k == "Return":
            niv = self.sel + 1
            if niv <= self.prog()["debloque"]:
                self.lancer_intro(niv)
            else:
                self.message = "Niveau verrouillé : réussis d'abord le niveau précédent."
        elif k.lower() == "c":
            self.j.etat = "th_clavier"
            self.sel = ORDRE.index(self.layout()) + 1
        elif k.lower() == "p":
            self.j.aller_pratique()
        elif k == "Escape":
            self.j.etat = "accueil"

    def touche_fin(self, k):
        r = self.res
        if k == "Return":
            if r["reussi"] and self.niv < NB_NIVEAUX_THEORIE:
                self.lancer_intro(self.niv + 1)
            elif r["reussi"]:
                self.j.aller_pratique()
            else:
                self.lancer_intro(self.niv)
        elif k.lower() == "r":
            self.lancer_intro(self.niv)
        elif k.lower() == "p":
            self.j.aller_pratique()
        elif k == "Escape":
            self.j.etat = "th_niveaux"
            self.sel = min(self.prog()["debloque"], NB_NIVEAUX_THEORIE) - 1

    # ------------------------------------------------------------ niveau
    def lancer_intro(self, niv):
        self.preparer()
        self.niv = niv
        self.cible = generer(niv, self.kb)
        self.idx = self.erreurs = 0
        self.reveles = set()
        self.flashs = {}
        self.lettres = {}
        self.t_debut = None
        self.erreurs_consec = 0
        self.indice_jusqu = 0.0
        self.j.etat = "th_intro"

    def commencer(self):
        self.t_debut = None
        self.j.etat = "th_jeu"

    def touche_jeu(self, e):
        k = e.keysym
        if k == "Escape":
            self.j.etat = "th_niveaux"
            self.sel = self.niv - 1
            return
        if k == "Tab":
            self.j.aller_pratique()
            return
        if k == "F1":
            self.j.data["guide_doigts"] = not self.j.data["guide_doigts"]
            stockage.sauver(self.j.data)
            return
        ch = e.char
        if not ch or not ch.isprintable():
            return
        now = time.time()
        if self.t_debut is None:
            self.t_debut = now
        attendu = self.cible[self.idx]
        c = ch.lower() if ch.isalpha() else ch
        stat = None
        if attendu.isalpha():
            stat = self.lettres.setdefault(attendu, [0, 0])
            stat[1] += 1
        wpm = (self.idx / 5) / ((now - self.t_debut) / 60) if now - self.t_debut > 0.5 else 0
        if c == attendu:
            self.idx += 1
            self.reveles.add(attendu)
            self.flashs[attendu] = ("#4ade80", now + 0.35)
            self.erreurs_consec = 0
            self.j.son.clic(wpm)
            if self.idx >= len(self.cible):
                self.terminer(now)
        else:
            self.erreurs += 1
            self.erreurs_consec += 1
            if stat:
                stat[0] += 1
            if self.kb.pos(c):
                self.flashs[c] = ("#dc2626", now + 0.3)
            self.j.son.erreur()
            if self.erreurs_consec >= 2:         # coup de pouce : la bonne touche s'éclaire
                self.indice_jusqu = now + 1.8

    def precision(self):
        total = self.idx + self.erreurs
        return 100 if total == 0 else round(100 * self.idx / total)

    def terminer(self, now):
        duree = max(0.5, now - self.t_debut)
        wpm = round((self.idx / 5) / (duree / 60))
        prec = self.precision()
        info = stockage.enregistrer_theorie(self.j.data, self.layout(), self.niv, wpm, prec, self.lettres)
        ratees = sorted(((e, l) for l, (e, t) in self.lettres.items() if e > 0), reverse=True)[:4]
        tout_fini = stockage.niveaux_reussis(self.j.data) >= NB_NIVEAUX_THEORIE
        self.res = {"wpm": wpm, "precision": prec, "erreurs": self.erreurs,
                    "ratees": [l.upper() for _, l in ratees], "tout_fini": tout_fini, **info}
        if info["reussi"]:
            self.j.son.victoire()
        else:
            self.j.son.defaite()
        self.j.etat = "th_fin"

    # ------------------------------------------------------------ animation
    def maj(self, now, dt):
        et = self.j.etat
        if et in ("th_intro", "th_jeu"):
            self.preparer()
            doigt = cible = None
            if et == "th_jeu" and self.j.data["guide_doigts"] and self.idx < len(self.cible):
                attendu = self.cible[self.idx]
                doigt, cible = self.kb.doigt(attendu), self.kb.pos(attendu)
            self.mains.maj(dt, doigt, cible)

    # ------------------------------------------------------------ dessin
    def dessiner(self, now):
        et = self.j.etat
        if et == "th_clavier":
            self.dessiner_choix()
        elif et == "th_niveaux":
            self.dessiner_niveaux()
        elif et == "th_intro":
            self.dessiner_intro()
        elif et == "th_jeu":
            self.dessiner_jeu(now)
        elif et == "th_fin":
            self.dessiner_fin()

    def titre(self, texte, sous=None):
        p = self.j.p
        self.j.titre_fx(W // 2, 34, texte, 24)
        if sous:
            p.texte(W // 2, 68, text=sous, fill=GRIS, font=("Segoe UI", 11), width=820)

    def pied(self, texte):
        self.j.p.texte(W // 2, 545, text=texte, fill=GRIS, font=("Segoe UI", 10, "bold"))

    def clic(self, i, touche="Return"):
        """Clic sur une ligne : on la sélectionne puis on valide (comme ↑/↓ + ENTRÉE)."""
        self.sel = i
        self.j.simuler(touche)

    def dessiner_choix(self):
        p = self.j.p
        self.j.bouton_retour()
        self.titre("CHOISIS TON CLAVIER",
                   "Prends celui de ton ordinateur : les touches du jeu doivent correspondre à celles sous tes doigts.")
        detecte_id, expl = self.detection()
        entrees = [f"★  Par défaut : détecter le clavier de mon système  →  {LAYOUTS[detecte_id]['nom']}"]
        entrees += [f"{LAYOUTS[i]['nom']}   —   {LAYOUTS[i]['pays']}" for i in ORDRE]
        for i, texte in enumerate(entrees):
            y = 108 + i * 40
            actif = i == self.sel
            survol = self.j.dans(110, y - 17, 790, y + 17)
            p.rect(110, y - 17, 790, y + 17, r=12, fill=ACCENT if actif else (CARTE_HAUT if survol else CARTE),
                   outline="" if actif else (ACCENT if survol else BORD), width=2)
            p.texte(130, y, text=texte, anchor="w", fill=FOND if actif else BLANC,
                    font=("Segoe UI", 12, "bold"))
            self.j.zone(110, y - 17, 790, y + 17, lambda i=i: self.clic(i))
        if self.message:
            p.texte(W // 2, 352, text=self.message, fill=VERT, font=("Segoe UI", 11, "bold"))
        lid = detecte_id if self.sel == 0 else ORDRE[self.sel - 1]
        kb = Clavier(lid, 280, 372, 34)
        dessiner_clavier(p, kb, masque=False)
        self.pied("↑ / ↓ choisir    |    ENTRÉE valider    |    ÉCHAP retour    |    TAB mode pratique")

    def dessiner_niveaux(self):
        p = self.j.p
        prog = self.prog()
        nom = LAYOUTS[self.layout()]["nom"]
        self.titre("MODE THÉORIQUE", f"Clavier : {nom}   (touche C pour le changer)")
        for i, niv in enumerate(NIVEAUX):
            n = i + 1
            y = 118 + i * 58
            ok = n <= prog["debloque"]
            sc = prog["scores"].get(str(n))
            actif = i == self.sel
            survol = self.j.dans(110, y - 25, 790, y + 25)
            p.rect(110, y - 25, 790, y + 25, r=16, fill=ACCENT if actif else (CARTE_HAUT if survol else CARTE),
                   outline="" if actif else (ACCENT if survol else BORD), width=2)
            self.j.zone(110, y - 25, 790, y + 25, lambda i=i: self.clic(i))
            fg = FOND if actif else BLANC
            gris = "#1e3a5f" if actif else GRIS
            icone = ("✔" if sc and sc.get("reussi") else "▶") if ok else "🔒"
            p.texte(135, y, text=icone, fill=fg if ok else ROUGE, font=("Segoe UI", 15, "bold"))
            p.texte(175, y - 9, text=f"Niveau {n} — {niv['nom']}", anchor="w", fill=fg,
                    font=("Segoe UI", 13, "bold"))
            p.texte(175, y + 12, text=niv["court"], anchor="w", fill=gris, font=("Segoe UI", 9))
            if sc:
                etoiles = "★" * sc.get("etoiles", 0) + "☆" * (3 - sc.get("etoiles", 0))
                p.texte(775, y - 9, text=etoiles, anchor="e", fill=JAUNE if not actif else "#7a5c00",
                        font=("Segoe UI", 13, "bold"))
                p.texte(775, y + 12, text=f"{sc['precision']} %  ·  {sc['wpm']} WPM", anchor="e",
                        fill=gris, font=("Segoe UI", 9))
        reussis = stockage.niveaux_reussis(self.j.data)
        p.rect(110, 478, 790, 490, r=6, fill=CARTE, outline=BORD, width=1)
        if reussis:
            p.rect(110, 478, 110 + 680 * reussis / NB_NIVEAUX_THEORIE, 490, r=6, fill=VERT)
        if reussis >= NB_NIVEAUX_THEORIE:
            texte = "🎓 Théorie terminée ! Tu es prêt pour la course : appuie sur Tab ou P."
        else:
            texte = self.message or f"Progression : {reussis}/{NB_NIVEAUX_THEORIE} niveaux réussis"
        p.texte(W // 2, 510, text=texte, fill=JAUNE if reussis >= NB_NIVEAUX_THEORIE else GRIS,
                font=("Segoe UI", 11, "bold"))
        j = self.j
        j.bouton(110, 526, 330, 552, "⌨  Clavier  (C)", lambda: j.simuler("c"), taille=10, r=12)
        j.bouton(340, 526, 560, 552, "🏎  Mode pratique  (TAB)", lambda: j.simuler("Tab"), taille=10, r=12)
        j.bouton(570, 526, 790, 552, "🏠  Accueil  (ÉCHAP)", lambda: j.simuler("Escape"), taille=10, r=12)

    def dessiner_intro(self):
        p = self.j.p
        self.preparer()
        niv = NIVEAUX[self.niv - 1]
        self.titre(f"NIVEAU {self.niv} — {niv['nom'].upper()}")
        p.texte(W // 2, 98, text=niv["desc"], fill="#e2e8f0", font=("Segoe UI", 12), width=780)
        nouvelles = lettres_nouvelles(self.niv, self.kb)
        dessiner_clavier(p, self.kb, masque=False, nouvelles=nouvelles)
        self.mains.dessiner(p, noms=True)
        for i, ligne in enumerate(conseils_niveau(self.niv, self.kb)):
            p.texte(W // 2, 488 + i * 17, text="• " + ligne, fill=GRIS, font=("Segoe UI", 9), width=840)
        j = self.j
        j.bouton(190, 532, 450, 556, "▶  COMMENCER  (ENTRÉE)", lambda: j.simuler("Return"), fond=VERT_BOUTON,
                 fg=BLANC, taille=11, r=12)
        j.bouton(465, 532, 725, 556, "◀  Retour  (ÉCHAP)", lambda: j.simuler("Escape"), taille=11, r=12)

    def dessiner_jeu(self, now):
        p = self.j.p
        self.preparer()
        niv = NIVEAUX[self.niv - 1]
        total = len(self.cible)
        # barre de titre + progression
        p.texte(30, 20, text=f"NIVEAU {self.niv} · {niv['nom']}", anchor="w", fill=ACCENT,
                font=("Segoe UI", 14, "bold"))
        p.texte(870, 20, text=self.kb.nom, anchor="e", fill=GRIS, font=("Segoe UI", 12, "bold"))
        p.rect(30, 40, 870, 50, r=5, fill=CARTE, outline=BORD, width=1)
        if self.idx / total > 0.01:
            p.rect(30, 40, 30 + 840 * self.idx / total, 50, r=5, fill=VERT)

        # zone de lettres à taper
        p.rect(60, 62, 840, 142, r=18, fill=CARTE, outline=ACCENT, width=2)
        cw, cx0, cy0 = 30, 450, 102
        for i in range(self.idx - 12, self.idx + 14):
            if i < 0 or i >= total:
                continue
            x = cx0 + (i - self.idx) * cw
            if i < self.idx:
                col = VERT
            elif i == self.idx:
                col = "white"
                erreur = any(c == "#dc2626" and t > now for c, t in self.flashs.values())
                p.rect(x - cw // 2, cy0 - 24, x + cw // 2, cy0 + 24, fill=ROUGE if erreur else "#3b5bdb")
            else:
                col = "#cbd5e1"
            lettre = self.cible[i] if self.cible[i] != " " else "·"
            p.texte(x, cy0, text=lettre, fill=col, font=("Consolas", 28, "bold"))

        attendu = self.cible[self.idx] if self.idx < total else " "
        if self.j.data["guide_doigts"]:
            doigt = self.kb.doigt(attendu)
            p.texte(W // 2, 158, text=f"Doigt à utiliser :  {NOMS_DOIGTS[doigt]}", fill=JAUNE,
                    font=("Segoe UI", 11, "bold"))
        else:
            p.texte(W // 2, 158, text="Guide des doigts désactivé (F1 pour le remettre)", fill=GRIS,
                    font=("Segoe UI", 10))

        # clavier masqué + mains
        flashs = {c: col for c, (col, t) in self.flashs.items() if t > now}
        if now < self.indice_jusqu:
            flashs[attendu] = JAUNE_FLASH
        dessiner_clavier(p, self.kb, reveles=self.reveles, masque=True, flashs=flashs)
        self.mains.dessiner(p, doigt=self.kb.doigt(attendu) if self.j.data["guide_doigts"] else None)

        # statistiques
        duree = (now - self.t_debut) if self.t_debut else 0
        wpm = round((self.idx / 5) / (duree / 60)) if duree > 0.5 else 0
        nb_touches = len(self.kb.touches) + 1
        stats = [f"Vitesse : {wpm} WPM", f"Précision : {self.precision()} %",
                 f"Erreurs : {self.erreurs}", f"Touches découvertes : {len(self.reveles)}/{nb_touches}"]
        for i, s in enumerate(stats):
            p.texte(150 + i * 200, 492, text=s, fill="white", font=("Segoe UI", 11, "bold"))
        self.pied("ÉCHAP niveaux    |    F1 guide des doigts    |    TAB mode pratique")

    def dessiner_fin(self):
        p = self.j.p
        r = self.res
        p.rect(150, 70, 750, 500, r=24, fill=CARTE, outline=ACCENT, width=3)
        titre = "Niveau réussi !" if r["reussi"] else "Presque ! Encore un essai"
        p.texte(W // 2, 120, text=titre, fill=VERT if r["reussi"] else JAUNE, font=("Segoe UI", 28, "bold"))
        p.texte(W // 2, 170, text="★" * r["etoiles"] + "☆" * (3 - r["etoiles"]), fill=JAUNE,
                font=("Segoe UI", 34, "bold"))
        p.texte(W // 2, 225, text=f"{r['wpm']} WPM   ·   Précision {r['precision']} %   ·   {r['erreurs']} erreur(s)",
                fill="white", font=("Segoe UI", 13, "bold"))
        if not r["reussi"]:
            p.texte(W // 2, 260, text=f"Il faut {SEUIL_THEORIE} % de précision pour passer au niveau suivant. "
                    "Va moins vite, vise juste !", fill=GRIS, font=("Segoe UI", 11), width=520)
        if r["ratees"]:
            p.texte(W // 2, 305, text="Touches à retravailler :  " + "  ".join(r["ratees"]),
                    fill=ROUGE, font=("Segoe UI", 12, "bold"))
        if r["xp"]:
            p.texte(W // 2, 340, text=f"+{r['xp']} XP", fill=JAUNE, font=("Segoe UI", 14, "bold"))
        if r["reussi"] and r["tout_fini"]:
            p.texte(W // 2, 385, text="🎓 Bravo, tu as terminé tout le mode théorique !\n"
                    "Mets maintenant ta technique à l'épreuve dans la course.",
                    fill=JAUNE, justify="center", font=("Segoe UI", 12, "bold"), width=520)
            boutons = [("🏎  ALLER À LA COURSE (ENTRÉE)", "Return", True), ("Niveaux (ÉCHAP)", "Escape", False)]
        elif r["reussi"]:
            boutons = [("NIVEAU SUIVANT (ENTRÉE)", "Return", True), ("Rejouer (R)", "r", False),
                       ("Niveaux (ÉCHAP)", "Escape", False)]
        else:
            boutons = [("RÉESSAYER (ENTRÉE)", "Return", True), ("Niveaux (ÉCHAP)", "Escape", False)]
        j = self.j
        largeur = 560 / len(boutons)
        for i, (txt, touche, principal) in enumerate(boutons):
            x0 = 170 + i * largeur
            j.bouton(x0 + 4, 436, x0 + largeur - 4, 474, txt, lambda t=touche: j.simuler(t),
                     fond=VERT_BOUTON if principal else None, fg=BLANC if principal else None, taille=10, r=14)
        self.pied("P ou TAB : mode pratique")
