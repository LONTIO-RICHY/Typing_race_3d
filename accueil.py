"""Accueil : choix entre le mode théorique (apprendre) et le mode pratique (la course).

Explique l'intérêt de chaque mode et encourage à commencer par la théorie.
"""

import time
import tkinter as tk
import webbrowser

import stockage
from config import *


class Accueil:
    def __init__(self, jeu):
        self.j = jeu
        self.sel = 0          # 0 = théorique, 1 = pratique

    # ------------------------------------------------------------ clavier
    def touche(self, e):
        k = e.keysym
        j = self.j
        et = j.etat
        if et == "accueil":
            if k in ("Left", "Right", "Up", "Down"):
                self.sel = 1 - self.sel
            elif k == "Return":
                self.ouvrir(self.sel)
            elif k.lower() == "t":
                self.ouvrir(0)
            elif k.lower() == "p":
                self.ouvrir(1)
            elif k.lower() == "i":
                j.etat = "aide"
            elif k.lower() == "c":
                j.etat = "contact"
        elif et == "contact":
            if k in ("Escape", "Return"):
                j.etat = "accueil"
        elif et == "aide":
            if k in ("Escape", "Return"):
                j.etat = "accueil"
            elif k.lower() == "t":
                self.ouvrir(0)
            elif k.lower() == "p":
                self.ouvrir(1)
        elif et == "conseil":
            if k == "Return" or k.lower() == "t":
                j.conseil_vu = True
                self.ouvrir(0)
            elif k.lower() == "p":
                j.conseil_vu = True
                j.aller_pratique()
            elif k == "Escape":
                j.etat = "accueil"

    def ouvrir(self, mode):
        if mode == 0:
            self.j.aller_theorie()
        else:
            self.j.aller_pratique(avec_conseil=True)

    def ouverture(self):
        """Appelé quand on revient sur l'accueil : sélection conseillée."""
        self.sel = 0 if self.j.theorie_incomplete() else 1

    # ------------------------------------------------------------ dessin
    def dessiner(self, now):
        et = self.j.etat
        if et == "accueil":
            self.dessiner_accueil()
        elif et == "contact":
            self.dessiner_contact()
        elif et == "aide":
            self.dessiner_aide()
        else:
            self.dessiner_conseil()

    def carte(self, x0, y0, x1, y1, actif, titre, sous, lignes, badge, couleur_badge, statut, frac, mode):
        j = self.j
        p = j.p
        if j.dans(x0, y0, x1, y1):
            self.sel = mode                      # la souris sélectionne la carte survolée
            actif = True
        p.rect(x0, y0, x1, y1, r=20, fill=CARTE_HAUT if actif else CARTE,
               outline=ACCENT if actif else BORD, width=4 if actif else 2)
        j.zone(x0, y0, x1, y1, lambda: self.ouvrir(mode))
        p.texte(x0 + 20, y0 + 28, text=titre, anchor="w", fill=BLANC, font=("Segoe UI", 17, "bold"))
        p.texte(x0 + 20, y0 + 56, text=sous, anchor="w", fill=ACCENT, font=("Segoe UI", 11, "bold"))
        for i, ligne in enumerate(lignes):
            p.texte(x0 + 20, y0 + 92 + i * 34, text="•  " + ligne, anchor="w", fill="#dbe4f3",
                    font=("Segoe UI", 10), width=x1 - x0 - 40)
        p.rect(x0 + 20, y1 - 62, x1 - 20, y1 - 50, r=6, fill=FOND)
        if frac > 0.03:
            p.rect(x0 + 20, y1 - 62, x0 + 20 + (x1 - x0 - 40) * frac, y1 - 50, r=6, fill=VERT)
        p.texte(x0 + 20, y1 - 32, text=statut, anchor="w", fill=GRIS, font=("Segoe UI", 10, "bold"))
        if badge:
            p.rect(x1 - 215, y0 + 12, x1 - 14, y0 + 38, r=13, fill=couleur_badge)
            p.texte(x1 - 114, y0 + 25, text=badge, fill=FOND, font=("Segoe UI", 9, "bold"))

    def dessiner_accueil(self):
        p = self.j.p
        j = self.j
        reussis = stockage.niveaux_reussis(j.data)
        incomplet = j.theorie_incomplete()
        j.titre_fx(W // 2, 38, "TYPING RACE 3D", 34)
        p.texte(W // 2, 72, text="Apprends à taper vite, sans regarder le clavier", fill=GRIS,
                font=("Segoe UI", 12))

        if reussis >= NB_NIVEAUX_THEORIE:
            badge_t, col_t = "✔ TERMINÉ", VERT
        elif incomplet:
            badge_t, col_t = "★ RECOMMANDÉ EN PREMIER", JAUNE
        else:
            badge_t, col_t = "EN COURS", ACCENT
        self.carte(40, 95, 440, 395, self.sel == 0, "📘  MODE THÉORIQUE", "Apprendre à taper sans regarder",
                   ["Un clavier virtuel dont les touches sont cachées : tu les découvres en tapant",
                    "Des mains guides qui te montrent le bon doigt pour chaque touche",
                    "6 niveaux : base → voyelles → consonnes → mots français → mots anglais → défi"],
                   badge_t, col_t, f"Progression : {reussis}/{NB_NIVEAUX_THEORIE} niveaux réussis",
                   reussis / NB_NIVEAUX_THEORIE, 0)
        if incomplet:
            badge_p, col_p = "CONSEILLÉ APRÈS LA THÉORIE", "#cbd5e1"
        else:
            badge_p, col_p = "✔ TU ES PRÊT", VERT
        self.carte(460, 95, 860, 395, self.sel == 1, "🏎  MODE PRATIQUE", "La course 3D contre des adversaires",
                   ["Tape vite et juste pour faire avancer ta voiture et battre les autres pilotes",
                    "Garage, pistes, niveaux, XP et statistiques pour rester motivé",
                    "L'endroit pour mettre ta technique à l'épreuve, chrono en main"],
                   badge_p, col_p, f"Meilleur score : {j.data['meilleur']} WPM", 0, 1)

        p.rect(40, 408, 860, 522, r=18, fill="#171f4d", outline=JAUNE, width=2)
        p.texte(60, 426, text="💡  Pourquoi commencer par la théorie ?", anchor="w", fill=JAUNE,
                font=("Segoe UI", 12, "bold"))
        arguments = [
            "Taper vite, c'est taper SANS regarder : tes yeux restent sur le texte pendant que tes doigts connaissent chaque touche.",
            "Sans cette base, on prend de mauvaises habitudes (2 doigts, regarder ses mains) et on plafonne vite — puis c'est long à corriger.",
            "Quelques minutes de théorie suffisent pour bien démarrer, ensuite la course te fait progresser en vitesse.  (Touche I : en savoir plus)",
        ]
        for i, a in enumerate(arguments):
            p.texte(60, 452 + i * 24, text=a, anchor="w", fill="#e2e8f0", font=("Segoe UI", 9), width=780)
        p.texte(W // 2, 538, text="← / → choisir    |    ENTRÉE ouvrir    |    T théorie    |    P pratique    |    I pourquoi deux modes ?    |    C contact",
                fill=GRIS, font=("Segoe UI", 9, "bold"))
        self.signature()

    def signature(self):
        """Signature du créateur en bas de l'accueil (cliquable : ouvre l'écran Contact)."""
        j, p = self.j, self.j.p
        texte = f"Créé par {AUTEUR['nom']}  ·  un problème ? Contacte-moi (touche C)"
        survol = j.dans(W // 2 - 260, 549, W // 2 + 260, 560)
        p.texte(W // 2, 554, text=texte, fill=ACCENT if survol else GRIS, font=("Segoe UI", 8, "bold"))
        j.zone(W // 2 - 260, 549, W // 2 + 260, 560, lambda: j.simuler("c"))

    def copier(self, texte, nom):
        try:
            self.j.root.clipboard_clear()
            self.j.root.clipboard_append(texte)
            self.j.notice = (f"{nom} copié dans le presse-papiers", time.time() + 2.5)
        except tk.TclError:
            pass

    def ouvrir_lien(self, url):
        try:
            webbrowser.open(url)
        except Exception:
            self.copier(url, "Lien")

    def dessiner_contact(self):
        p, j = self.j.p, self.j
        j.bouton_retour()
        j.titre_fx(W // 2, 38, "CONTACTER LE CRÉATEUR", 26)
        p.texte(W // 2, 74, text=f"Jeu créé par {AUTEUR['nom']}", fill=BLANC, font=("Segoe UI", 14, "bold"))
        p.texte(W // 2, 100, text="Tu as rencontré un problème ? Écris-moi, je t'aiderai avec plaisir.",
                fill=GRIS, font=("Segoe UI", 11))
        lignes = [
            ("💬  WhatsApp", AUTEUR["whatsapp"], AUTEUR["whatsapp_lien"], VERT_BOUTON),
            ("✉  E-mail", AUTEUR["email"], "mailto:" + AUTEUR["email"], ACCENT),
            ("</>  GitHub", AUTEUR["github"], AUTEUR["github"], ACCENT2),
        ]
        for i, (titre, valeur, lien, col) in enumerate(lignes):
            y0 = 135 + i * 100
            survol = j.dans(60, y0, 840, y0 + 84)
            p.rect(60, y0, 840, y0 + 84, r=18, fill=CARTE_HAUT if survol else CARTE, outline=col, width=2)
            p.texte(86, y0 + 24, text=titre, anchor="w", fill=col, font=("Segoe UI", 12, "bold"))
            p.texte(86, y0 + 54, text=valeur, anchor="w", fill=BLANC, font=("Consolas", 15, "bold"))
            j.bouton(600, y0 + 14, 820, y0 + 42, "Ouvrir", lambda l=lien: self.ouvrir_lien(l), taille=10, r=8,
                     fond=col, fg=FOND)
            j.bouton(600, y0 + 46, 820, y0 + 74, "Copier", lambda v=valeur, n=titre.split("  ")[-1]: self.copier(v, n),
                     taille=10, r=8)
        p.texte(W // 2, 450, text="Pour m'aider à comprendre : dis-moi ce que tu faisais, et joins le fichier erreurs.log "
                "(à côté du jeu) s'il existe.", fill="#cbd5e1", font=("Segoe UI", 10), width=760)
        p.texte(W // 2, 545, text="ÉCHAP / ENTRÉE retour", fill=GRIS, font=("Segoe UI", 9, "bold"))

    def dessiner_aide(self):
        p = self.j.p
        self.j.bouton_retour()
        self.j.titre_fx(W // 2, 34, "À QUOI SERT CHAQUE MODE ?", 24)
        p.texte(W // 2, 66, text="C'est comme apprendre à conduire avant de faire la course.", fill=GRIS,
                font=("Segoe UI", 11))
        colonnes = [
            (40, "📘  Mode théorique — APPRENDRE", [
                "Tu apprends où est chaque touche et quel doigt l'utilise : c'est la mémoire musculaire.",
                "Le clavier est masqué : tu es obligé de ne pas regarder, et c'est ce qui crée le réflexe.",
                "Les mains guides montrent la bonne technique dès le début, avant les mauvaises habitudes.",
                "Des niveaux progressifs, du plus simple (rangée de base) aux mots entiers.",
                "Sans lui : on tape à 2 doigts, on regarde ses mains, la vitesse se bloque et les erreurs reviennent.",
            ]),
            (460, "🏎  Mode pratique — S'ENTRAÎNER", [
                "Tu mets la technique en situation, sous pression : chrono et adversaires.",
                "Tu gagnes en vitesse et en régularité, comme un sportif qui joue des matchs.",
                "XP, niveaux, garage, pistes et statistiques te gardent motivé.",
                "Le mode entraînement travaille tes lettres les plus difficiles.",
                "Sans lui : tu connais le clavier mais tu restes lent, faute d'entraînement.",
            ]),
        ]
        for x0, titre, lignes in colonnes:
            p.rect(x0, 90, x0 + 400, 400, r=20, fill=CARTE, outline=BORD, width=2)
            p.texte(x0 + 18, 114, text=titre, anchor="w", fill=BLANC, font=("Segoe UI", 13, "bold"))
            for i, l in enumerate(lignes):
                p.texte(x0 + 18, 158 + i * 47, text="•  " + l, anchor="w", fill="#dbe4f3",
                        font=("Segoe UI", 10), width=364)
        p.rect(40, 414, 860, 522, r=18, fill="#171f4d", outline=JAUNE, width=2)
        p.texte(60, 434, text="NOTRE CONSEIL", anchor="w", fill=JAUNE, font=("Segoe UI", 12, "bold"))
        p.texte(60, 478, anchor="w", fill="#e2e8f0", font=("Segoe UI", 10), width=780,
                text="1) Fais d'abord les niveaux 1 à 3 de la théorie : base, voyelles, consonnes.\n"
                     "2) Lance-toi ensuite dans la course, puis alterne : un peu de théorie, une course, et ainsi de suite.\n"
                     "3) Tu peux passer d'un mode à l'autre à tout moment avec la touche TAB.")
        p.texte(W // 2, 545, text="ÉCHAP / ENTRÉE retour    |    T théorie    |    P pratique", fill=GRIS,
                font=("Segoe UI", 9, "bold"))

    def dessiner_conseil(self):
        j = self.j
        p = j.p
        reussis = stockage.niveaux_reussis(j.data)
        p.rect(100, 100, 800, 460, r=24, fill=CARTE, outline=JAUNE, width=3)
        p.texte(W // 2, 148, text="💡  Avant la course…", fill=JAUNE, font=("Segoe UI", 26, "bold"))
        p.texte(W // 2, 262, fill="#e2e8f0", font=("Segoe UI", 12), justify="center", width=620,
                text=f"Tu n'as pas encore terminé les bases du mode théorique ({reussis}/{NB_NIVEAUX_THEORIE} niveaux).\n\n"
                     "Sans technique, on finit par taper en regardant le clavier et la vitesse plafonne vite.\n"
                     "Quelques minutes de théorie maintenant te feront gagner énormément de temps ensuite.")
        j.bouton(160, 345, 740, 392, "ENTRÉE ou T  :  faire la théorie d'abord  (recommandé)",
                 lambda: j.simuler("Return"), fond=VERT_BOUTON, fg=BLANC, taille=13, r=16)
        j.bouton(160, 402, 740, 440, "P  :  jouer quand même", lambda: j.simuler("p"), taille=12, r=14)
        j.bouton_retour("◀  Accueil")
