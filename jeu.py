"""Logique et affichage du jeu (course de frappe en 3D)."""

import math
import random
import time
import tkinter as tk
import traceback
import types

import dessin as d
import stockage
from chemins import chemin_ressource, dossier_donnees
from accueil import Accueil
from arrivee import dessiner_arrivee
from champions import FORMATS, Champions
from config import *
from effets import Particules
from moteur3d import melanger
from musique import PLAYLIST, Musique
from outils import fmt_chrono, fmt_duree, parse_duree
import schema
from scene3d import Scene3D
from son import Son
from theorie import Theorie

LISTES = {"modele": MODELES, "couleur": COULEURS, "piste": PISTES}
VOIES_BOTS = [0, 2, 3]
VOIES_DUEL = [2]                # duel contre un boss : côte à côte avec toi (tu es sur la voie 1)
NOMS_QUALITE = {1: "Légère", 2: "Normale", 3: "Élevée"}

# Touches de difficulté : sur un clavier AZERTY, « 1 2 3 » sans Maj donnent & é " (et non 1 2 3)
TOUCHES_DIFFICULTE = {
    "1": "1", "ampersand": "1", "KP_1": "1", "KP_End": "1",
    "2": "2", "eacute": "2", "KP_2": "2", "KP_Down": "2",
    "3": "3", "quotedbl": "3", "KP_3": "3", "KP_Next": "3",
}

# Sur AZERTY, les chiffres de la saisie de durée sont atteints sans Maj
AZERTY_CHIFFRES = {"ampersand": "1", "eacute": "2", "quotedbl": "3", "apostrophe": "4", "parenleft": "5",
                   "minus": "6", "egrave": "7", "underscore": "8", "ccedilla": "9", "agrave": "0"}

TEMPS_LISSAGE = 0.28        # secondes : plus c'est grand, plus la voiture glisse doucement
IMAGES_PAR_SECONDE = 60
LOG_ERREURS = dossier_donnees() / "erreurs.log"


def lisser(pos, vel, cible, temps_lissage, dt):
    """Ressort amorti critique : la position rejoint la cible en douceur, sans à-coups de vitesse.

    Contrairement à un simple « position += (cible - position) * k », la VITESSE varie
    progressivement : la voiture ne démarre plus et ne s'arrête plus à chaque touche tapée.
    Retourne (nouvelle position, nouvelle vitesse).
    """
    omega = 2.0 / temps_lissage
    x = omega * dt
    amorti = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x)
    ecart = pos - cible
    tmp = (vel + omega * ecart) * dt
    vel = (vel - omega * tmp) * amorti
    pos = cible + (ecart + tmp) * amorti
    return pos, vel


class Bot:
    """Adversaire réaliste : il accélère, ralentit et trébuche."""

    def __init__(self, nom, couleur, modele, wpm):
        self.nom, self.couleur, self.modele = nom, couleur, modele
        self.wpm_base = wpm
        self.pos = 0.0
        self.mult = 1.0
        self.reste = random.uniform(0.5, 1.5)

    def maj(self, dt, pos_joueur=None):
        self.reste -= dt
        if self.reste <= 0:
            r = random.random()
            if r < 0.15:        # il fait une erreur et ralentit
                self.mult = random.uniform(0.15, 0.45)
                self.reste = random.uniform(0.4, 0.9)
            elif r < 0.35:      # rafale de vitesse
                self.mult = random.uniform(1.25, 1.5)
                self.reste = random.uniform(0.8, 1.6)
            else:               # rythme normal
                self.mult = random.uniform(0.9, 1.1)
                self.reste = random.uniform(1.0, 2.2)
        self.pos += self.wpm_base * 5 / 60 * self.mult * dt


def vitesse_relative(p_erreur, p_rafale):
    """Multiplicateur moyen d'un boss (fautes + rafales + rythme normal), pour viser exactement son WPM."""
    p_norm = 1.0 - p_erreur - p_rafale
    haut = p_erreur * 0.65 * 0.30 + p_rafale * 1.2 * 1.375 + p_norm * 1.6 * 1.0
    bas = p_erreur * 0.65 + p_rafale * 1.2 + p_norm * 1.6
    return haut / bas


class BossBot(Bot):
    """Boss : comme un adversaire, mais avec un caractère (fautes, rafales, départ, rattrapage, final)."""

    def __init__(self, cfg, but):
        super().__init__(cfg["nom"], cfg["couleur"], cfg["modele"],
                         cfg["wpm"] / vitesse_relative(cfg["p_erreur"], cfg["p_rafale"]))
        self.cfg, self.but, self.temps = cfg, float(but), 0.0

    def maj(self, dt, pos_joueur=None):
        c = self.cfg
        self.temps += dt
        self.reste -= dt
        if self.reste <= 0:
            r = random.random()
            if r < c["p_erreur"]:                       # faute : il ralentit
                self.mult = random.uniform(0.15, 0.45)
                self.reste = random.uniform(0.4, 0.9)
            elif r < c["p_erreur"] + c["p_rafale"]:     # rafale
                self.mult = random.uniform(1.25, 1.5)
                self.reste = random.uniform(0.8, 1.6)
            else:                                       # rythme normal
                self.mult = random.uniform(0.9, 1.1)
                self.reste = random.uniform(1.0, 2.2)
        mult = self.mult
        if self.temps < 4.0:                            # départ : le multiplicateur retombe à 1 en 4 s
            mult *= 1.0 + (c["depart"] - 1.0) * (1.0 - self.temps / 4.0)
        if self.pos > 0.75 * self.but:                  # dernière ligne droite
            mult *= c["final"]
        if pos_joueur is not None and c["rattrapage"] > 0:
            retard = pos_joueur - self.pos              # > 0 : tu es devant
            if retard > 6:
                mult *= 1.0 + c["rattrapage"] * min(1.0, (retard - 6) / 30.0)
        self.pos += self.wpm_base * 5 / 60 * mult * dt


class Jeu:
    def __init__(self, root):
        self.root = root
        root.title("Typing Race 3D")
        try:                                     # icône de la fenêtre (Windows)
            root.iconbitmap(str(chemin_ressource("icone_typing_race.ico")))
        except Exception:
            pass
        root.resizable(True, True)               # bouton agrandir de Windows + glisser les bords
        root.minsize(W // 2, H // 2)
        self.c = tk.Canvas(root, width=W, height=H, bg=FOND, highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.p = d.Peintre(self.c)
        self.c.bind("<Configure>", self.on_resize)
        self.plein_ecran = False
        self.scene = Scene3D(self.p)

        self.data = stockage.charger()
        self.son = Son(self.data["muet"])
        self.part = Particules()
        self.mus = Musique()
        self.mus.regler_volume(self.data["volume"], self.data["muet"])
        self.mus_sel = 0
        self.conseil_vu = False
        self.th = Theorie(self)
        self.champ = Champions(self)
        self.acc = Accueil(self)
        self.acc.ouverture()
        root.bind("<Key>", self.on_key)
        self.c.bind("<Motion>", self.on_motion)
        self.c.bind("<Button-1>", self.on_click)
        self.c.bind("<Leave>", self.on_quitte)

        self.etat = "accueil"    # accueil / aide / conseil / contact / th_* (théorie) / menu (pratique) / boss / musique / garage / stats / saisie (durée) / comp_* (compétitions) / countdown / race / end
        self.diff = "2"
        self.langue = "fr"
        self.duree_s = self.data["duree"]    # durée choisie (secondes, libre jusqu'à 30 jours)
        self.mode = "course"     # course / entrainement
        self.nav = {k: self.data[k] for k in LISTES}

        self.cle_statique = None
        self.dernier = time.time()
        self.cible = ""
        self.idx = self.erreurs = 0
        self.err_until = 0
        self.derniere_touche = 0
        self.t0 = self.t_start = self.t_fin = self.t_terminee = 0
        self.z_aff = 0.0
        self.v_aff = 0.0                 # vitesse visuelle de la voiture (lissage)
        self.dernier_bip = None
        self.bots = []
        self.boss = None                 # boss affronté (duel), ou None
        self.boss_sel = 0
        self.lettres_course = {}
        self.faibles = []
        self.resultat = {}
        self.duree = self.duree_s
        self.goal = 180

        # souris : zones cliquables reconstruites à chaque image, listes déroulantes, saisie de durée
        self.zones = []
        self.superposes = []
        self.souris = (-100.0, -100.0)
        self.curseur = ""
        self.liste_ouverte = None
        self.liste_etat = None
        self.liste_union = None
        self.saisie = ""
        self.saisie_msg = ""
        self.etat_avant = "menu"

        # compétitions et arrivée
        self.comp = None
        self.arrivee_t = None
        self.fin_type = ""
        self.dernier_tour = 0

        # fluidité : cadence réelle, affichage F3, baisse automatique de qualité si le PC peine
        self.periode = 1.0 / IMAGES_PAR_SECONDE      # durée moyenne d'une image (lissée)
        self.afficher_fps = False
        self.lent_depuis = None
        self.derniere_baisse = 0.0
        self.notice = ("", 0.0)
        self.erreurs_vues = set()
        self.erreurs_consec = 0
        self.prochain = time.perf_counter()

        self.loop()

    # ------------------------------------------------------------ utilitaires
    def niveau(self):
        return stockage.niveau_de(self.data["xp"])

    def choisir_mot(self):
        mots = MOTS[self.langue][1]
        if self.mode == "entrainement" and self.faibles and random.random() < 0.8:
            pool = [m for m in mots if any(l in m for l in self.faibles)]
            if pool:
                return random.choice(pool)
        return random.choice(mots)

    def etendre_cible(self, minimum):
        while len(self.cible) < minimum:
            self.cible += (" " if self.cible else "") + self.choisir_mot()

    def wpm_actuel(self, t):
        return (self.idx / 5) / (t / 60) if t > 0.5 else 0

    def precision(self):
        total = self.idx + self.erreurs
        return 100 if total == 0 else round(100 * self.idx / total)

    def t_actuel(self, now):
        if self.etat == "race":
            return now - self.t_start
        if self.etat == "end":
            return self.t_fin
        return 0

    def z_arrivee(self):
        longueur = self.goal * M_PAR_CHAR
        if self.mode == "course":
            return longueur
        return (math.floor(self.z_aff / longueur) + 1) * longueur

    def voitures_3d(self):
        liste = [{"nom": "TOI", "x": VOIES_X[VOIE_JOUEUR], "z": self.z_aff, "joueur": True,
                  "modele": self.data["modele"], "couleur": COULEURS[self.data["couleur"]]["hex"]}]
        voies = VOIES_DUEL if self.boss else VOIES_BOTS
        for i, b in enumerate(self.bots):
            rang = i // len(voies)               # au-delà de 4 voitures : rangées successives sur la grille
            z = b.pos * M_PAR_CHAR - rang * 6.0 * max(0.0, 1.0 - b.pos / 15.0)
            liste.append({"nom": b.nom, "x": VOIES_X[voies[i % len(voies)]], "z": z,
                          "modele": b.modele, "couleur": b.couleur})
        return liste

    def nouveau_bot(self, nom, couleur, modele, wpm):
        return Bot(nom, couleur, modele, wpm)

    # ------------------------------------------------------------ modes
    def theorie_incomplete(self):
        """Vrai tant que les 3 premiers niveaux théoriques (base, voyelles, consonnes) ne sont pas réussis."""
        return stockage.niveaux_reussis(self.data) < 3

    def aller_theorie(self):
        self.mus.arreter()
        self.th.ouvrir()

    def aller_pratique(self, avec_conseil=False):
        self.mus.arreter()
        if avec_conseil and self.theorie_incomplete() and not self.conseil_vu:
            self.etat = "conseil"
        else:
            self.etat = "menu"

    def aller_accueil(self):
        self.mus.arreter()
        self.acc.ouverture()
        self.etat = "accueil"

    # ------------------------------------------------------------ déroulement
    def demarrer(self):
        self.duree = self.duree_s
        self.faibles = stockage.lettres_faibles(self.data)
        if self.mode == "course":
            self.goal = self.duree * CHARS_PAR_SECONDE
            if self.boss:                                   # duel : toi contre le boss, rien d'autre
                self.bots = [BossBot(self.boss, self.goal)]
            elif self.comp:                                 # compétition : tous les pilotes en lice
                self.bots = self.comp.creer_bots(self)
            else:
                vitesses = DIFFICULTES[self.diff][1]
                self.bots = [Bot(nom, col, mod, w + random.randint(-3, 3))
                             for (nom, col, mod), w in zip(BOTS, vitesses)]
        else:
            self.goal = TOUR_ENTRAINEMENT
            self.bots = []
        self.cible = ""
        self.etendre_cible(400)               # le texte s'allonge au fil de la frappe (courses de 24 h et plus)
        self.arrivee_t = None
        self.fin_type = ""
        self.dernier_tour = 0
        if self.comp:
            self.comp.debut_course(self)
        self.idx = self.erreurs = 0
        self.z_aff = 0.0
        self.v_aff = 0.0
        self.lettres_course = {}
        self.err_until = 0
        self.derniere_touche = 0
        self.dernier_bip = None
        self.part.vider()
        self.t0 = time.time()
        self.etat = "countdown"
        choix = self.data["musique"]
        if choix:
            self.mus.jouer(choix)
        else:
            self.mus.arreter()

    def terminer(self, t, place_force=None, fin=None):
        self.t_fin = min(t, self.duree)
        self.t_terminee = time.time()
        self.etat = "end"
        if fin is None:
            if self.mode == "course" and self.idx >= self.goal:
                fin = "arrivee"
            else:
                fin = "temps" if t >= self.duree else "adversaire"
        self.fin_type = fin
        self.mus.arreter(800)
        wpm = round(self.wpm_actuel(self.t_fin))
        place = None
        if self.mode == "course":
            place = 1 + sum(1 for b in self.bots if min(float(self.goal), b.pos) > self.idx)
            if place_force is not None:
                place = place_force
            if self.boss:
                xp = wpm + {1: 50, 2: 10}.get(place, 0)
            else:
                xp = wpm + {1: 50, 2: 25, 3: 10}.get(place, 0)
        else:
            xp = wpm // 2

        precedent = next((h["wpm"] for h in reversed(self.data["historique"])
                          if h.get("mode") == self.mode), None)
        record = wpm > self.data["meilleur"]
        ancien_niveau = self.niveau()
        premiere = bool(self.boss and place == 1 and self.idx >= 5
                        and self.boss["id"] not in self.data["boss_vaincus"])
        if premiere:
            xp += self.boss["bonus_xp"]
        if self.idx >= 5:    # on n'enregistre pas une course abandonnée
            entree = {
                "wpm": wpm, "precision": self.precision(), "place": place,
                "duree": self.duree, "diff": self.diff, "langue": self.langue,
                "mode": self.mode,
            }
            if self.boss:
                entree["boss"] = self.boss["id"]
            if self.comp:
                entree["comp"] = self.comp.format
            if premiere:
                self.data["boss_vaincus"].append(self.boss["id"])
            stockage.enregistrer(self.data, entree, self.lettres_course, xp)
        else:
            xp = 0
            record = False
        nouveau_niveau = self.niveau()
        self.resultat = {
            "wpm": wpm, "precision": self.precision(), "erreurs": self.erreurs,
            "place": place, "xp": xp, "precedent": precedent, "record": record,
            "niveau": nouveau_niveau if nouveau_niveau > ancien_niveau else None,
            "debloque": stockage.deblocages(ancien_niveau, nouveau_niveau),
            "boss": self.boss, "boss_premiere": premiere,
        }
        if self.comp:
            self.comp.fin_manche(self)
        if self.mode == "course" and place == 1:
            self.son.victoire()
            self.part.confettis()
        elif self.mode == "course":
            self.son.defaite()
        else:
            self.son.victoire()

    # ------------------------------------------------------------ clavier
    def on_resize(self, e):
        """La fenêtre change de taille : le jeu est redessiné à la nouvelle échelle."""
        self.p.regler(e.width, e.height)

    def basculer_plein_ecran(self):
        self.plein_ecran = not self.plein_ecran
        try:
            self.root.attributes("-fullscreen", self.plein_ecran)
        except Exception:
            self.plein_ecran = False
            return
        if self.plein_ecran:
            self.notice = ("Plein écran : appuie sur F11 pour revenir en fenêtre", time.time() + 3.5)

    def on_key(self, e):
        try:
            self._on_key(e)
        except Exception:
            self.signaler_erreur()

    def _on_key(self, e):
        if e.keysym == "KP_Enter":              # Entrée du pavé numérique = Entrée
            e.keysym = "Return"
        k = e.keysym
        if k == "F3":                           # compteur d'images par seconde
            self.afficher_fps = not self.afficher_fps
            return
        if k == "F11":                          # plein écran
            self.basculer_plein_ecran()
            return
        if k == "Escape" and self.liste_ouverte and self.etat not in ("race", "th_jeu"):
            self.liste_ouverte = None             # Échap referme d'abord la liste déroulante
            return
        if self.etat == "saisie":                 # ici on tape une durée : « m » = minutes, pas de raccourcis
            self.touche_saisie(e)
            return
        if self.etat == "th_jeu":                 # ici les lettres sont tapées, pas de raccourcis
            self.th.touche(e)
            return
        if self.etat == "race":
            self.touche_course(e)
            return
        if self.etat == "countdown":
            if k == "Escape":
                self.retour_menu()
            return
        if k.lower() == "m":
            self.data["muet"] = not self.data["muet"]
            self.son.muet = self.data["muet"]
            self.mus.regler_volume(self.data["volume"], self.data["muet"])
            stockage.sauver(self.data)
            return
        if self.etat in ("accueil", "aide", "conseil", "contact"):
            self.acc.touche(e)
        elif self.etat.startswith("th_"):
            self.th.touche(e)
        elif self.etat == "menu":
            self.touche_menu(k)
        elif self.etat == "musique":
            self.touche_musique(k)
        elif self.etat == "garage":
            self.touche_garage(k)
        elif self.etat == "stats":
            if k in ("Escape", "Return"):
                self.etat = "menu"
        elif self.etat == "boss":
            self.touche_boss(k)
        elif self.etat.startswith("comp_"):
            self.champ.touche(e)
        elif self.etat == "end":
            if k == "Return":
                if self.comp:
                    self.champ.apres_course()   # classement de la compétition
                else:
                    self.demarrer()             # revanche (même boss s'il y en a un)
            elif k == "Escape":
                self.retour_menu()

    def retour_menu(self):
        """Sortie d'une course : liste des boss si c'était un duel, sinon menu."""
        if self.comp:
            self.champ.abandon()
            return
        self.part.vider()
        self.mus.arreter()
        self.etat = "boss" if self.boss else "menu"

    def touche_menu(self, k):
        if k == "Tab":
            self.aller_theorie()
        elif k == "Escape":
            self.aller_accueil()
        elif k in TOUCHES_DIFFICULTE:
            self.diff = TOUCHES_DIFFICULTE[k]
        elif k.lower() == "d":
            self.duree_suivante()
        elif k.lower() == "u":
            self.ouvrir_saisie()
        elif k.lower() == "c":
            self.champ.ouvrir()
        elif k.lower() == "f":
            self.langue = "fr"
        elif k.lower() == "e":
            self.langue = "en"
        elif k.lower() == "t":
            self.mode = "entrainement" if self.mode == "course" else "course"
        elif k.lower() == "q":
            self.data["qualite"] = self.data["qualite"] % 3 + 1
            stockage.sauver(self.data)
        elif k.lower() == "g":
            self.nav = {c: self.data[c] for c in LISTES}
            self.etat = "garage"
        elif k.lower() == "s":
            self.etat = "stats"
        elif k.lower() == "b":
            self.ouvrir_boss()
        elif k == "Return":
            self.boss = None                    # course normale
            self.comp = None
            self.valider_depart()

    def touche_diff(self, k):
        return TOUCHES_DIFFICULTE.get(k)

    # ---- durée de course libre
    def regler_duree(self, secondes):
        self.duree_s = int(max(DUREE_MIN, min(DUREE_MAX, secondes)))
        self.data["duree"] = self.duree_s
        stockage.sauver(self.data)

    def duree_suivante(self):
        i = DUREES.index(self.duree_s) + 1 if self.duree_s in DUREES else 0
        self.regler_duree(DUREES[i % len(DUREES)])

    def ouvrir_saisie(self):
        self.saisie, self.saisie_msg = "", ""
        self.etat_avant = self.etat
        self.liste_ouverte = None
        self.etat = "saisie"

    def touche_saisie(self, e):
        k = e.keysym
        if k == "Escape":
            self.etat = self.etat_avant
        elif k == "Return":
            s = parse_duree(self.saisie)
            if s is None:
                self.saisie_msg = "Durée non reconnue. Exemples : 90 · 5 min · 2h · 1h30 · 24h · 3j"
            elif s < DUREE_MIN:
                self.saisie_msg = f"Trop court : minimum {DUREE_MIN} secondes"
            elif s > DUREE_MAX:
                self.saisie_msg = f"Trop long : maximum {fmt_duree(DUREE_MAX)}"
            else:
                self.regler_duree(s)
                self.etat = self.etat_avant
                self.notice = (f"Durée de course : {fmt_duree(s)}", time.time() + 3.0)
        elif k == "BackSpace":
            self.saisie, self.saisie_msg = self.saisie[:-1], ""
        else:
            ch = AZERTY_CHIFFRES.get(k, e.char)      # sur AZERTY les chiffres sont atteints sans Maj
            if ch and ch.isprintable() and len(self.saisie) < 16:
                self.saisie += ch
                self.saisie_msg = ""

    def valider_depart(self):
        """Choix de la musique si tu as des sons, sinon départ direct."""
        self.mus.pistes = self.mus.scanner()
        if self.mus.actif and self.mus.pistes:
            n = len(self.mus.pistes)
            noms = [f.name for f in self.mus.pistes]
            saved = self.data["musique"]
            if saved == PLAYLIST and n >= 2:
                self.mus_sel = n + 1
            elif saved in noms:
                self.mus_sel = noms.index(saved) + 1
            else:
                self.mus_sel = 0
            self.etat = "musique"
        else:
            self.demarrer()

    # ---- défis boss
    def boss_debloque(self, b):
        return self.niveau() >= b["niveau"]

    def boss_vaincu(self, b):
        return b["id"] in self.data["boss_vaincus"]

    def ouvrir_boss(self):
        """Ouvre la liste des boss, sur le prochain à battre."""
        choix = 0
        for i, b in enumerate(BOSSES):
            if self.boss_debloque(b):
                choix = i
                if not self.boss_vaincu(b):
                    break
        self.boss_sel = choix
        self.etat = "boss"

    def touche_boss(self, k):
        if k == "Escape":
            self.etat = "menu"
        elif k in ("Up", "Down"):
            self.boss_sel = (self.boss_sel + (1 if k == "Down" else -1)) % len(BOSSES)
        elif k.lower() == "d":
            self.duree_suivante()
        elif k.lower() == "u":
            self.ouvrir_saisie()
        elif k == "Return":
            b = BOSSES[self.boss_sel]
            if not self.boss_debloque(b):
                self.notice = (f"Atteins le niveau {b['niveau']} pour défier {b['nom']} (tu es niveau {self.niveau()})",
                               time.time() + 3.5)
            else:
                self.boss = b
                self.comp = None
                self.mode = "course"
                self.valider_depart()

    def nb_choix_musique(self):
        n = len(self.mus.pistes)
        return n + 1 + (1 if n >= 2 else 0)       # aucune + sons + playlist

    def apercu_musique(self):
        n = len(self.mus.pistes)
        if self.mus_sel == 0:
            self.mus.arreter()
        elif self.mus_sel <= n:
            self.mus.jouer(self.mus.pistes[self.mus_sel - 1].name)
        else:
            self.mus.jouer(PLAYLIST)

    def touche_musique(self, k):
        n = len(self.mus.pistes)
        if k in ("Up", "Down"):
            self.mus_sel = (self.mus_sel + (1 if k == "Down" else -1)) % self.nb_choix_musique()
            self.apercu_musique()
        elif k in ("Left", "Right"):
            v = self.data["volume"] + (0.1 if k == "Right" else -0.1)
            self.data["volume"] = round(max(0.0, min(1.0, v)), 1)
            self.mus.regler_volume(self.data["volume"], self.data["muet"])
            stockage.sauver(self.data)
        elif k == "Return":
            if self.mus_sel == 0:
                self.data["musique"] = ""
            elif self.mus_sel <= n:
                self.data["musique"] = self.mus.pistes[self.mus_sel - 1].name
            else:
                self.data["musique"] = PLAYLIST
            stockage.sauver(self.data)
            self.mus.arreter()
            self.demarrer()
        elif k == "Escape":
            self.mus.arreter()
            if self.comp:
                self.champ.abandon(False)
            else:
                self.etat = "boss" if self.boss else "menu"

    def changer(self, cle, delta):
        liste = LISTES[cle]
        self.nav[cle] = (self.nav[cle] + delta) % len(liste)
        if self.niveau() >= liste[self.nav[cle]]["niveau"]:
            self.data[cle] = self.nav[cle]       # équipé automatiquement
            stockage.sauver(self.data)

    def touche_garage(self, k):
        if k == "Left":
            self.changer("modele", -1)
        elif k == "Right":
            self.changer("modele", 1)
        elif k == "Up":
            self.changer("couleur", -1)
        elif k == "Down":
            self.changer("couleur", 1)
        elif k.lower() == "p":
            self.changer("piste", 1)
        elif k in ("Escape", "Return"):
            self.etat = "menu"

    def touche_course(self, e):
        if e.keysym == "Escape":
            self.retour_menu()
            return
        ch = e.char
        if not ch or not ch.isprintable():
            return
        now = time.time()
        attendu = self.cible[self.idx]
        c = ch.lower() if ch.isalpha() else ch     # Verrouillage Majuscules / Maj ne comptent plus comme erreur
        stat = None
        if attendu.isalpha():
            stat = self.lettres_course.setdefault(attendu, [0, 0])
            stat[1] += 1
        if c == attendu:
            self.idx += 1
            self.derniere_touche = now
            if len(self.cible) - self.idx < 60:
                self.etendre_cible(len(self.cible) + 120)
            self.son.clic(self.wpm_actuel(now - self.t_start))
        else:
            self.erreurs += 1
            if stat:
                stat[0] += 1
            self.err_until = now + 0.15
            self.son.erreur()
            self.part.etincelles(*self.scene.ancre_joueur)

    # ------------------------------------------------------------ boucle
    def loop(self):
        now = time.time()
        reel = max(0.0, now - self.dernier)
        self.dernier = now
        dt = min(0.25, reel)                    # vrai temps écoulé : les adversaires ne ralentissent plus si le PC peine
        try:
            self.maj(now, dt)
            self.draw(now)
            self.maj_survol()
            self.erreurs_consec = 0
        except Exception:
            self.signaler_erreur()
            self.erreurs_consec += 1
            if self.erreurs_consec == 30:       # écran bloqué sur une erreur répétée : retour à l'accueil
                self.erreurs_consec = 0
                try:
                    self.part.vider()
                    self.aller_accueil()
                except Exception:
                    pass
        self.mesurer_cadence(now, reel)
        # image suivante : 60 par seconde visées, sans attente inutile quand on est en retard
        t = time.perf_counter()
        self.prochain += 1.0 / IMAGES_PAR_SECONDE
        delai = int((self.prochain - t) * 1000)
        if delai < 1:
            delai = 1
            self.prochain = t
        self.root.after(delai, self.loop)

    def mesurer_cadence(self, now, reel):
        """Cadence réelle + baisse automatique de la qualité 3D si elle reste sous ~30 images/s."""
        if 0.0 < reel < 1.0:
            self.periode += (reel - self.periode) * 0.1
        if self.etat != "race" or now - self.t_start < 1.5 or self.data["qualite"] <= 1:
            self.lent_depuis = None
            return
        if self.periode > 0.036:                # moins de ~28 images/s
            if self.lent_depuis is None:
                self.lent_depuis = now
            elif now - self.lent_depuis > 1.5 and now - self.derniere_baisse > 3.0:
                self.data["qualite"] -= 1
                stockage.sauver(self.data)
                self.derniere_baisse = now
                self.lent_depuis = None
                self.notice = (f"Qualité 3D réduite pour rester fluide : {NOMS_QUALITE[self.data['qualite']]}",
                               now + 4.0)
        else:
            self.lent_depuis = None

    def signaler_erreur(self):
        """Note l'erreur dans erreurs.log (une seule fois par type d'erreur) sans arrêter le jeu."""
        texte = traceback.format_exc()
        try:
            self.root.title("Typing Race 3D — erreur interne (voir erreurs.log)")
        except Exception:
            pass
        signature = texte.strip().splitlines()[-1] if texte.strip() else "?"
        cle = (self.etat, signature)
        if cle in self.erreurs_vues:
            return
        self.erreurs_vues.add(cle)
        try:
            with open(LOG_ERREURS, "a", encoding="utf-8") as f:
                f.write(f"--- {time.strftime('%d/%m/%Y %H:%M:%S')}  (état : {self.etat})\n{texte}\n"
                        f"Un problème ? Contacte {AUTEUR['nom']} : WhatsApp {AUTEUR['whatsapp']} | "
                        f"{AUTEUR['email']} | {AUTEUR['github']}\n\n")
        except OSError:
            pass

    def maj(self, now, dt):
        self.part.maj(dt)
        self.mus.maj()
        if self.etat.startswith("th_"):
            self.th.maj(now, dt)
        if self.etat == "countdown":
            reste = 3 - (now - self.t0)
            if reste <= 0:
                self.etat = "race"
                self.t_start = now
                self.son.depart()
            else:
                n = math.ceil(reste)
                if n != self.dernier_bip:
                    self.dernier_bip = n
                    self.son.bip()
        elif self.etat == "race":
            t = now - self.t_start
            wpm = self.wpm_actuel(t)
            cible = self.idx * M_PAR_CHAR
            self.z_aff, self.v_aff = lisser(self.z_aff, self.v_aff, cible, TEMPS_LISSAGE, dt)
            if self.z_aff > cible:              # jamais en avance sur ce qui a été tapé
                self.z_aff, self.v_aff = cible, min(self.v_aff, 0.0)
            for b in self.bots:
                b.maj(dt, self.idx)
            if wpm > 15 and random.random() < dt * wpm / 9:
                self.part.fumee(*self.scene.ancre_joueur)
            if self.comp and self.comp.maj_course(self, t):
                return                          # élimination : la course est déjà terminée
            if self.mode == "entrainement":    # petit drapeau à chaque tour bouclé
                tour = int(self.z_aff // (self.goal * M_PAR_CHAR))
                if tour > self.dernier_tour:
                    self.dernier_tour = tour
                    self.arrivee_t = now
            fini = t >= self.duree
            if self.mode == "course" and (
                    self.idx >= self.goal or any(b.pos >= self.goal for b in self.bots)):
                fini = True
            if fini:
                self.terminer(t)
        elif self.etat == "end":
            # la voiture et les adversaires finissent leur course (animation)
            if self.mode == "course":
                for b in self.bots:
                    b.maj(dt, self.idx)
                self.z_aff, self.v_aff = lisser(self.z_aff, self.v_aff, self.idx * M_PAR_CHAR + 10, 0.6, dt)
                if self.arrivee_t is None:      # drapeau : dès que la voiture franchit la ligne
                    if self.fin_type == "arrivee" and self.z_aff >= self.z_arrivee() - 1.0:
                        self.arrivee_t = now
                    elif self.fin_type == "survivant":
                        self.arrivee_t = self.t_terminee

    # ------------------------------------------------------------ souris
    def zone(self, x0, y0, x1, y1, action, liste=None):
        """Déclare une zone cliquable pour cette image (action = fonction sans argument)."""
        self.zones.append((x0, y0, x1, y1, action, liste))

    def zone_sous(self, x, y):
        for z in reversed(self.zones):               # la dernière dessinée est celle du dessus
            if z[0] <= x <= z[2] and z[1] <= y <= z[3]:
                return z
        return None

    def dans(self, x0, y0, x1, y1):
        x, y = self.souris
        return x0 <= x <= x1 and y0 <= y <= y1

    def simuler(self, keysym, char=""):
        """Un clic sur un bouton = la touche clavier correspondante."""
        self.on_key(types.SimpleNamespace(keysym=keysym, char=char))

    def on_motion(self, e):
        try:
            self.souris = self.p.vers_jeu(e.x, e.y)
            self.maj_survol()
        except Exception:
            self.signaler_erreur()

    def on_quitte(self, e):
        self.souris = (-100.0, -100.0)
        self.maj_survol()

    def on_click(self, e):
        try:
            self.souris = self.p.vers_jeu(e.x, e.y)
            z = self.zone_sous(*self.souris)
            if self.liste_ouverte and not self.dans_liste(*self.souris) and (z is None or z[5] != self.liste_ouverte):
                self.liste_ouverte = None            # clic en dehors de la liste ouverte : on la referme
            if z is not None and z[4]:
                z[4]()
        except Exception:
            self.signaler_erreur()

    def maj_survol(self):
        """Curseur en main gantée sur ce qui est cliquable ; ouverture/fermeture des listes déroulantes."""
        x, y = self.souris
        z = self.zone_sous(x, y)
        if z and z[5] and OUVRIR_AU_SURVOL and self.liste_ouverte != z[5]:
            self.ouvrir_liste(z[5])
        elif OUVRIR_AU_SURVOL and self.liste_ouverte and self.liste_union is not None:
            if not self.dans_liste(x, y):
                self.liste_ouverte = None            # mode survol : le curseur a quitté la liste
        curseur = "hand2" if (z and z[4]) else ""
        if curseur != self.curseur:
            self.curseur = curseur
            try:
                self.c.config(cursor=curseur)
            except Exception:
                pass

    def ouvrir_liste(self, ident):
        self.liste_ouverte = ident
        self.liste_etat = self.etat

    def basculer_liste(self, ident):
        """Clic sur le bouton d'une liste : l'ouvre, ou la referme si elle était déjà ouverte."""
        if self.liste_ouverte == ident and not OUVRIR_AU_SURVOL:
            self.liste_ouverte = None
        else:
            self.ouvrir_liste(ident)

    def dans_liste(self, x, y):
        """Vrai si le point est dans la liste déroulante actuellement ouverte (bouton + menu)."""
        if self.liste_ouverte is None or self.liste_union is None:
            return False
        ux0, uy0, ux1, uy1 = self.liste_union
        return ux0 <= x <= ux1 and uy0 <= y <= uy1

    # ---- éléments d'interface
    def bouton(self, x0, y0, x1, y1, texte, action, actif=False, taille=12, fond=None, fg=None,
               r=12, desactive=False):
        p = self.p
        survol = (not desactive) and action is not None and self.dans(x0, y0, x1, y1)
        if actif:
            fill, bord, col = ACCENT, ACCENT, FOND
        elif fond:
            fill, bord, col = (melanger(fond, "#ffffff", 0.2) if survol else fond), "", fg or BLANC
        else:
            fill = CARTE_HAUT if survol else CARTE
            bord, col = (ACCENT if survol else BORD), fg or (GRIS if desactive else BLANC)
        p.rect(x0, y0, x1, y1, r=r, fill=fill, outline=bord, width=2)
        p.texte((x0 + x1) / 2, (y0 + y1) / 2, text=texte, fill=col, font=("Segoe UI", taille, "bold"))
        if action is not None and not desactive:
            self.zone(x0, y0, x1, y1, action)

    def pill(self, cx, cy, w, h, texte, actif=False, taille=12, action=None):
        self.bouton(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, texte, action, actif, taille)

    def liste(self, ident, cx, cy, w, h, texte, options, courant, action, taille=12):
        """Bouton + liste déroulante. options = [(texte affiché, valeur)], action(valeur) au choix."""
        p = self.p
        x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        ouvert = self.liste_ouverte == ident
        vif = ouvert or self.dans(x0, y0, x1, y1)
        p.rect(x0, y0, x1, y1, r=12, fill=CARTE_HAUT if vif else CARTE,
               outline=ACCENT if vif else BORD, width=2)
        p.texte(cx - 8, cy, text=texte, fill=BLANC, font=("Segoe UI", taille, "bold"))
        p.texte(x1 - 15, cy, text="▲" if ouvert else "▼", fill=ACCENT, font=("Segoe UI", 8))
        self.zone(x0, y0, x1, y1, lambda: self.basculer_liste(ident), ident)
        if ouvert:
            self.superposes.append(lambda: self.dessiner_liste(x0, y0, x1, y1, options, courant, action))

    def dessiner_liste(self, x0, y0, x1, y1, options, courant, action):
        p = self.p
        hauteur = len(options) * 28 + 10
        haut = y1 if y1 + hauteur <= H - 4 else y0 - hauteur         # pas de place en bas : elle s'ouvre vers le haut
        bas = haut + hauteur
        self.liste_union = (x0, min(y0, haut), x1, max(y1, bas))
        p.rect(x0 + 3, haut + 4, x1 + 3, bas + 4, r=12, fill="#02040f")            # ombre
        p.rect(x0, haut, x1, bas, r=12, fill="#0d1545", outline=ACCENT, width=2)
        for i, (nom, val) in enumerate(options):
            ya, yb = haut + 5 + i * 28, haut + 5 + (i + 1) * 28
            actif = val == courant
            survol = self.dans(x0 + 4, ya, x1 - 4, yb)
            if survol or actif:
                p.rect(x0 + 6, ya + 1, x1 - 6, yb - 1, r=8, fill=ACCENT if survol else CARTE_HAUT)
            p.texte(x0 + 18, (ya + yb) / 2, text=nom, anchor="w",
                    fill=FOND if survol else (ACCENT if actif else BLANC),
                    font=("Segoe UI", 11, "bold" if actif else "normal"))
            if actif:
                p.texte(x1 - 18, (ya + yb) / 2, text="✔", fill=FOND if survol else VERT, font=("Segoe UI", 10, "bold"))
            self.zone(x0 + 4, ya, x1 - 4, yb, lambda v=val: self.choisir(action, v))

    def choisir(self, action, valeur):
        self.liste_ouverte = None
        action(valeur)

    def liste_duree(self, ident, cx, cy, w, h, taille=12, prefixe="Durée"):
        """Liste des durées rapides + « Saisir une durée… » (de 5 s à 30 jours)."""
        opts = [(fmt_duree(s), s) for s in DUREES]
        if self.duree_s not in DUREES:
            opts.insert(0, (fmt_duree(self.duree_s) + "  (perso)", self.duree_s))
        opts.append(("✎  Saisir une durée…", "saisie"))

        def choix(v):
            if v == "saisie":
                self.ouvrir_saisie()
            else:
                self.regler_duree(v)
        self.liste(ident, cx, cy, w, h, f"{prefixe} : {fmt_duree(self.duree_s)}", opts, self.duree_s, choix, taille)

    def regler_qualite(self, v):
        self.data["qualite"] = v
        stockage.sauver(self.data)

    # ------------------------------------------------------------ décor
    def titre_fx(self, x, y, texte, taille=30, couleur=ACCENT):
        self.p.texte(x + 2, y + 3, text=texte, fill="#02040f", font=("Segoe UI", taille, "bold"))
        self.p.texte(x, y, text=texte, fill=couleur, font=("Segoe UI", taille, "bold"))

    def fond_menu(self):
        """Dégradé indigo + halos de couleur (dessiné une seule fois)."""
        p = self.p
        n = 36
        for i in range(n):
            p.rect(0, H * i / n, W, H * (i + 1) / n + 1, fill=melanger(FOND, FOND2, i / (n - 1)))
        for cx, cy, r, col in ((70, 60, 200, "#1d2f8f"), (850, 520, 240, "#4c1d95"), (810, 40, 130, "#0e7490")):
            base = melanger(FOND, FOND2, cy / H)
            for k in range(6):
                rr = r * (1 - k * 0.16)
                p.oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=melanger(base, col, 0.05 + 0.05 * k))

    def bouton_retour(self, texte="◀  Retour"):
        self.bouton(16, 14, 140, 42, texte, lambda: self.simuler("Escape"), taille=10, r=10)

    # ------------------------------------------------------------ dessin
    def draw(self, now):
        scene = "course" if self.etat in ("countdown", "race", "end") else "autre"
        cle = (scene, self.data["piste"], self.p.taille)     # le fond fixe est redessiné si la fenêtre change de taille
        if cle != self.cle_statique:
            self.c.delete("all")
            self.p.tag = "static"
            if scene == "course":
                self.scene.fond_statique(PISTES[self.data["piste"]])
            else:
                self.fond_menu()
            self.p.tag = "dyn"
            self.cle_statique = cle
        self.c.delete("dyn")
        self.zones, self.superposes, self.liste_union = [], [], None
        if self.liste_ouverte and self.liste_etat != self.etat:
            self.liste_ouverte = None
        if self.etat in ("accueil", "aide", "conseil", "contact"):
            self.acc.dessiner(now)
        elif self.etat.startswith("th_"):
            self.th.dessiner(now)
        elif self.etat == "menu":
            self.dessiner_menu()
        elif self.etat == "boss":
            self.dessiner_boss()
        elif self.etat == "musique":
            self.dessiner_musique()
        elif self.etat == "garage":
            self.dessiner_garage(now)
        elif self.etat == "stats":
            self.dessiner_stats()
        elif self.etat == "saisie":
            self.dessiner_saisie()
        elif self.etat.startswith("comp_"):
            self.champ.dessiner(now)
        else:
            self.dessiner_course(now)
        for dessiner_dessus in self.superposes:          # listes déroulantes : toujours au-dessus
            dessiner_dessus()
        self.p.masque()                         # bandes autour du jeu en plein écran
        if now < self.notice[1]:
            demi = min(420, 18 + 3.6 * len(self.notice[0]))
            self.p.rect(W // 2 - demi, 62, W // 2 + demi, 88, r=12, fill=HUD, outline=JAUNE, width=1)
            self.p.texte(W // 2, 75, text=self.notice[0], fill=JAUNE, font=("Segoe UI", 11, "bold"))
        if self.afficher_fps:
            fps = 1.0 / self.periode if self.periode > 0 else 0
            self.p.rect(W - 112, H - 30, W - 8, H - 8, r=6, fill=HUD)
            self.p.texte(W - 60, H - 19, text=f"{fps:3.0f} img/s", fill=VERT if fps >= 45 else JAUNE if fps >= 28 else ROUGE,
                         font=("Consolas", 11, "bold"))

    # ---- menu
    def dessiner_menu(self):
        p = self.p
        self.titre_fx(W // 2, 44, "TYPING RACE 3D", 38)

        xp = self.data["xp"]
        niv = self.niveau()
        p.texte(W // 2 - 250, 92, text=f"Niveau {niv}", anchor="w", fill=JAUNE, font=("Segoe UI", 13, "bold"))
        p.rect(W // 2 - 130, 85, W // 2 + 170, 99, r=7, fill=CARTE, outline=BORD, width=1)
        if niv >= NIVEAU_MAX:
            frac, etiquette = 1.0, "MAX"
        else:
            frac = stockage.xp_dans_niveau(xp) / XP_PAR_NIVEAU
            etiquette = f"{stockage.xp_dans_niveau(xp)}/{XP_PAR_NIVEAU} XP"
        if frac > 0.02:
            p.rect(W // 2 - 130, 85, W // 2 - 130 + 300 * frac, 99, r=7, fill=JAUNE)
        p.texte(W // 2 + 180, 92, text=etiquette, anchor="w", fill=GRIS, font=("Segoe UI", 10))

        p.texte(W // 2, 126, text="Difficulté  (touches 1 / 2 / 3)", fill=GRIS, font=("Segoe UI", 10, "bold"))
        for n, (cle, (nom, _)) in enumerate(DIFFICULTES.items()):
            cx = W // 2 - 200 + n * 200
            self.bouton(cx - 85, 142, cx + 85, 178, f"{cle} - {nom}", lambda c=cle: setattr(self, "diff", c),
                        actif=cle == self.diff)

        y = 216
        self.liste_duree("duree", W // 2 - 315, y, 200, 34, 11)
        self.liste("langue", W // 2 - 105, y, 200, 34, f"Langue : {MOTS[self.langue][0]}",
                   [(MOTS[k][0], k) for k in MOTS], self.langue, lambda v: setattr(self, "langue", v), 11)
        self.liste("mode", W // 2 + 105, y, 200, 34,
                   f"Mode : {'Course' if self.mode == 'course' else 'Entraînement'}",
                   [("Course", "course"), ("Entraînement", "entrainement")], self.mode,
                   lambda v: setattr(self, "mode", v), 11)
        self.liste("qualite", W // 2 + 315, y, 200, 34, f"Qualité : {NOMS_QUALITE[self.data['qualite']]}",
                   [(NOMS_QUALITE[k], k) for k in (1, 2, 3)], self.data["qualite"], self.regler_qualite, 11)

        self.bouton(W // 2 - 160, 262, W // 2 + 160, 318, "JOUER  (ENTRÉE)", lambda: self.simuler("Return"),
                    fond=VERT_BOUTON, fg=BLANC, taille=19, r=20)

        son = "🔇  Son coupé (M)" if (self.data["muet"] or not self.son.actif) else "🔊  Son (M)"
        rangee = [("🏎  Garage (G)", "g"), ("📊  Stats (S)", "s"), ("👑  Boss (B)", "b"),
                  ("🏆  Compét. (C)", "c"), (son, "m")]
        for i, (txt, touche) in enumerate(rangee):
            cx = W // 2 + (i - 2) * 172
            self.bouton(cx - 82, 346, cx + 82, 382, txt, lambda t=touche: self.simuler(t), taille=10)
        self.bouton(W // 2 - 270, 394, W // 2 - 10, 428, "📘  Mode théorique (TAB)", lambda: self.simuler("Tab"), taille=11)
        self.bouton(W // 2 + 10, 394, W // 2 + 270, 428, "🏠  Accueil (ÉCHAP)", lambda: self.simuler("Escape"), taille=11)

        p.texte(W // 2, 456, text=f"Meilleur score : {self.data['meilleur']} WPM    |    "
                f"Boss vaincus : {len(self.data['boss_vaincus'])}/{len(BOSSES)}", fill="#cbd5e1", font=("Segoe UI", 11))
        faibles = stockage.lettres_faibles(self.data)
        if faibles:
            p.texte(W // 2, 478, text=f"Lettres à travailler : {', '.join(faibles)}  (mode Entraînement)",
                    fill=GRIS, font=("Segoe UI", 10))
        if not self.mus.actif:
            info = f"Musique : {self.mus.erreur}"
        elif not self.mus.pistes:
            info = "Musique : crée un dossier « sons » et mets-y 1.mp3, 2.mp3, 3.mp3 ..."
        else:
            choix = self.data["musique"]
            choix = "playlist en boucle" if choix == PLAYLIST else (choix or "aucune")
            info = f"{len(self.mus.pistes)} son(s) trouvé(s) — choix au lancement (dernier : {choix[:28]})"
        p.texte(W // 2, 498, text=info, fill=GRIS, font=("Segoe UI", 10))
        if self.theorie_incomplete():
            p.texte(W // 2, 524, text="💡 Conseil : fais d'abord le mode théorique pour taper plus vite et plus juste.",
                    fill=JAUNE, font=("Segoe UI", 10, "bold"))
        p.texte(W // 2, 546, text="D / U : durée libre   ·   Q : qualité   ·   F11 : plein écran   ·   F3 : images/s",
                fill="#64748b", font=("Segoe UI", 9))

    # ---- saisie d'une durée libre
    def mettre_saisie(self, texte):
        self.saisie, self.saisie_msg = texte, ""

    def ajouter_saisie(self, texte):
        if texte == "⌫":
            self.saisie = self.saisie[:-1]
        elif len(self.saisie) < 16:
            self.saisie += texte
        self.saisie_msg = ""

    def dessiner_saisie(self):
        p = self.p
        self.titre_fx(W // 2, 42, "DURÉE DE LA COURSE", 28)
        p.texte(W // 2, 80, text="Écris la durée que tu veux : de 5 secondes à 30 jours", fill=GRIS, font=("Segoe UI", 11))
        p.rect(200, 104, 700, 166, r=16, fill=CARTE, outline=ACCENT, width=3)
        if self.saisie:
            curseur = "▏" if int(time.time() * 2) % 2 == 0 else " "
            p.texte(W // 2, 135, text=self.saisie + curseur, fill=BLANC, font=("Segoe UI", 26, "bold"))
        else:
            p.texte(W // 2, 135, text="ex : 90 · 5 min · 2h · 1h30 · 24h · 3j", fill="#64748b", font=("Segoe UI", 14))
        s = parse_duree(self.saisie) if self.saisie else None
        if self.saisie_msg:
            p.texte(W // 2, 188, text=self.saisie_msg, fill=ROUGE, font=("Segoe UI", 11, "bold"))
        elif s is not None:
            bon = DUREE_MIN <= s <= DUREE_MAX
            p.texte(W // 2, 188, text=f"= {fmt_duree(s)}" + ("" if bon else "   (hors limites)"),
                    fill=VERT if bon else ROUGE, font=("Segoe UI", 13, "bold"))
        elif self.saisie:
            p.texte(W // 2, 188, text="…", fill=GRIS, font=("Segoe UI", 13))
        else:
            p.texte(W // 2, 188, text=f"Durée actuelle : {fmt_duree(self.duree_s)}", fill=GRIS, font=("Segoe UI", 11))

        rapides = ["15 s", "1 min", "5 min", "30 min", "1 h", "6 h", "24 h", "7 j"]
        for i, txt in enumerate(rapides):
            x = 62 + i * 102
            self.bouton(x, 212, x + 92, 242, txt, lambda t=txt: self.mettre_saisie(t), taille=10, r=10)

        for i, touche in enumerate(["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "⌫"]):
            col, lig = (i % 3, i // 3) if i < 9 else ((0, 3) if touche == "0" else (1, 3))
            cx, cy = 230 + col * 84, 292 + lig * 58
            self.bouton(cx - 36, cy - 25, cx + 36, cy + 25, touche, lambda t=touche: self.ajouter_saisie(t), taille=16, r=12)
        for i, (txt, ajout) in enumerate((("secondes", " s"), ("minutes", " min"), ("heures", " h"), ("jours", " j"))):
            cy = 292 + i * 58
            self.bouton(500, cy - 25, 620, cy + 25, txt, lambda a=ajout: self.ajouter_saisie(a), taille=12, r=12)
        self.bouton(660, 267, 860, 327, "✔  VALIDER  (ENTRÉE)", lambda: self.simuler("Return"),
                    fond=VERT_BOUTON, fg=BLANC, taille=12, r=16)
        self.bouton(660, 342, 860, 392, "Annuler  (ÉCHAP)", lambda: self.simuler("Escape"), taille=11, r=14)
        p.texte(W // 2, 522, text="Au clavier : tape la durée puis ENTRÉE    ·    la course peut durer 24 h, 3 jours…",
                fill=GRIS, font=("Segoe UI", 10))

    # ---- défis boss
    def dessiner_boss(self):
        p = self.p
        niv = self.niveau()
        self.bouton_retour()
        self.titre_fx(W // 2, 36, "DÉFIS BOSS", 28)
        p.texte(W // 2, 80, text="Un duel : toi contre le boss, il n'y a que 2 places. Chaque boss se débloque à un niveau.",
                fill=GRIS, font=("Segoe UI", 11))
        for i, b in enumerate(BOSSES):
            y = 150 + i * 84
            libre, vaincu = self.boss_debloque(b), self.boss_vaincu(b)
            survol = self.dans(100, y - 38, 800, y + 38)
            actif = i == self.boss_sel or survol
            p.rect(100, y - 38, 800, y + 38, r=16, fill=CARTE_HAUT if actif else CARTE,
                   outline=ACCENT if actif else BORD, width=3 if i == self.boss_sel else 2)
            p.rect(120, y - 26, 172, y + 26, r=12, fill=b["couleur"] if libre else "#334155")
            p.texte(146, y, text=str(b["niveau"]) if libre else "🔒", fill=FOND if libre else BLANC,
                    font=("Segoe UI", 20, "bold"))
            p.texte(192, y - 19, text=b["nom"] + ("  ✔" if vaincu else ""), anchor="w",
                    fill=BLANC if libre else GRIS, font=("Segoe UI", 15, "bold"))
            p.texte(192, y + 3, text=f"{b['style']} — {b['desc']}", anchor="w",
                    fill="#cbd5e1" if libre else "#64748b", font=("Segoe UI", 10))
            p.texte(192, y + 23, text=f"≈ {b['wpm']} WPM   |   1re victoire : +{b['bonus_xp']} XP", anchor="w",
                    fill=JAUNE if libre else "#64748b", font=("Segoe UI", 10))
            if vaincu:
                etat, col = "VAINCU", VERT
            elif libre:
                etat, col = "À BATTRE", JAUNE
            else:
                etat, col = f"Niveau {b['niveau']}", GRIS
            p.texte(780, y, text=etat, anchor="e", fill=col, font=("Segoe UI", 13, "bold"))
            self.zone(100, y - 38, 800, y + 38, lambda i=i: self.clic_boss(i))
        p.texte(W // 2, 494, text="↑ / ↓ : choisir    |    ENTRÉE ou clic : défier    |    D / U : durée    |    ÉCHAP : retour",
                fill=ACCENT, font=("Segoe UI", 10, "bold"))
        self.liste_duree("b_duree", 135, 528, 220, 32, 11)
        p.texte(W - 24, 528, text=f"Tu es niveau {niv}   |   Boss vaincus : {len(self.data['boss_vaincus'])}/{len(BOSSES)}",
                anchor="e", fill=GRIS, font=("Segoe UI", 10))

    def clic_boss(self, i):
        self.boss_sel = i
        self.simuler("Return")

    # ---- choix de la musique
    def clic_musique(self, i):
        if i == self.mus_sel:
            self.simuler("Return")
        else:
            self.mus_sel = i
            self.apercu_musique()

    def volume_souris(self):
        v = (self.souris[0] - 230) / 300
        self.data["volume"] = round(max(0.0, min(1.0, v)), 1)
        self.mus.regler_volume(self.data["volume"], self.data["muet"])
        stockage.sauver(self.data)

    def dessiner_musique(self):
        p = self.p
        n = len(self.mus.pistes)
        self.bouton_retour()
        self.titre_fx(W // 2, 45, "CHOISIS TA MUSIQUE", 30)
        p.texte(W // 2, 85, text="↑ / ↓ ou clic : écouter    |    ← / → : volume    |    ENTRÉE ou 2e clic : valider et jouer",
                fill=GRIS, font=("Segoe UI", 11))
        noms = ["✖  Aucune musique"] + ["♪  " + Musique.titre(f) + "  (en boucle)" for f in self.mus.pistes]
        if n >= 2:
            noms.append("🔁  Tous mes sons à la suite, en boucle")
        visibles = 8
        debut = max(0, min(self.mus_sel - 3, len(noms) - visibles))
        for i in range(debut, min(len(noms), debut + visibles)):
            y = 135 + (i - debut) * 46
            actif = i == self.mus_sel
            survol = self.dans(150, y - 19, 750, y + 19)
            p.rect(150, y - 19, 750, y + 19, r=14, fill=ACCENT if actif else (CARTE_HAUT if survol else CARTE),
                   outline="" if actif else (ACCENT if survol else BORD), width=2)
            p.texte(175, y, text=noms[i][:52], anchor="w", fill=FOND if actif else BLANC, font=("Segoe UI", 13, "bold"))
            self.zone(150, y - 19, 750, y + 19, lambda i=i: self.clic_musique(i))
        if len(noms) > visibles:
            p.texte(W // 2, 505, text=f"{self.mus_sel + 1} / {len(noms)}", fill=GRIS, font=("Segoe UI", 10))
        vol = self.data["volume"]
        p.texte(150, 535, text="Volume", anchor="w", fill=BLANC, font=("Segoe UI", 11, "bold"))
        p.rect(230, 528, 530, 542, r=7, fill=CARTE, outline=BORD, width=1)
        if vol > 0.03:
            p.rect(230, 528, 230 + 300 * vol, 542, r=7, fill=VERT)
        self.zone(220, 520, 540, 550, self.volume_souris)
        p.texte(545, 535, text="coupé (M)" if self.data["muet"] else f"{round(vol * 100)}%",
                anchor="w", fill=GRIS, font=("Segoe UI", 10))
        self.bouton(640, 516, 870, 552, "▶  JOUER  (ENTRÉE)", lambda: self.simuler("Return"),
                    fond=VERT_BOUTON, fg=BLANC, taille=12, r=14)

    # ---- garage (voiture 3D qui tourne)
    def dessiner_garage(self, now):
        p = self.p
        niv = self.niveau()
        modele = MODELES[self.nav["modele"]]
        couleur = COULEURS[self.nav["couleur"]]
        piste = PISTES[self.nav["piste"]]

        self.bouton_retour()
        self.titre_fx(W // 2, 38, "GARAGE", 30)
        p.texte(W // 2, 74, text=f"Niveau {niv} — gagne de l'XP pour tout débloquer", fill=GRIS, font=("Segoe UI", 11))
        self.scene.apercu_voiture(self.nav["modele"], couleur["hex"], piste, now * 0.9, 120, 95, 780, 300)
        self.bouton(44, 178, 92, 226, "◀", lambda: self.changer("modele", -1), taille=18, r=24)
        self.bouton(808, 178, 856, 226, "▶", lambda: self.changer("modele", 1), taille=18, r=24)

        lignes = [("Modèle (← / →)", modele, "modele"), ("Couleur (↑ / ↓)", couleur, "couleur"),
                  ("Piste (P)", piste, "piste")]
        for i, (titre, it, cle) in enumerate(lignes):
            y = 330 + i * 34
            ok = niv >= it["niveau"]
            p.texte(150, y, text=titre, anchor="w", fill=BLANC, font=("Segoe UI", 12, "bold"))
            p.texte(360, y, text=it["nom"], anchor="w", fill=ACCENT, font=("Segoe UI", 13, "bold"))
            p.texte(540, y, text="✔ équipé" if ok else f"🔒 Niveau {it['niveau']} requis",
                    anchor="w", fill=VERT if ok else ROUGE, font=("Segoe UI", 11, "bold"))
            self.bouton(730, y - 13, 766, y + 13, "◀", lambda c=cle: self.changer(c, -1), taille=10, r=8)
            self.bouton(774, y - 13, 810, y + 13, "▶", lambda c=cle: self.changer(c, 1), taille=10, r=8)

        for i, col in enumerate(COULEURS):
            cx = W // 2 - 245 + i * 70
            ok = niv >= col["niveau"]
            p.oval(cx - 17, 450, cx + 17, 484, fill=col["hex"], stipple="" if ok else "gray50")
            if i == self.nav["couleur"]:
                p.oval(cx - 22, 445, cx + 22, 489, fill="", outline=BLANC, width=3)
            elif self.dans(cx - 22, 445, cx + 22, 489):
                p.oval(cx - 22, 445, cx + 22, 489, fill="", outline=ACCENT, width=2)
            if not ok:
                p.texte(cx, 502, text=f"Niv. {col['niveau']}", fill=GRIS, font=("Segoe UI", 8))
            self.zone(cx - 22, 445, cx + 22, 489, lambda i=i: self.choisir_couleur(i))
        p.texte(W // 2, 535, text="Échap : retour au menu", fill=GRIS, font=("Segoe UI", 10))

    def choisir_couleur(self, i):
        self.nav["couleur"] = i
        self.changer("couleur", 0)

    # ---- statistiques
    def dessiner_stats(self):
        p = self.p
        self.bouton_retour()
        self.titre_fx(W // 2, 30, "STATISTIQUES", 22)

        p.rect(30, 62, 440, 545, r=18, fill=CARTE, outline=BORD, width=2)
        p.texte(235, 85, text="Top 10 des meilleurs scores", fill=BLANC, font=("Segoe UI", 12, "bold"))
        top = self.data["top"]
        if not top:
            p.texte(235, 300, text="Aucune course enregistrée", fill=GRIS, font=("Segoe UI", 11))
        for i, e in enumerate(top):
            y = 122 + i * 41
            p.texte(48, y, text=f"{i + 1}.", anchor="w", fill=JAUNE if i < 3 else ACCENT, font=("Segoe UI", 13, "bold"))
            p.texte(80, y, text=f"{e['wpm']} WPM", anchor="w", fill=BLANC, font=("Segoe UI", 13, "bold"))
            p.texte(178, y, text=f"{e['precision']}%", anchor="w", fill=VERT, font=("Segoe UI", 11))
            p.texte(228, y, text=e.get("date", ""), anchor="w", fill=GRIS, font=("Segoe UI", 10))
            p.texte(278, y, text=fmt_duree(e["duree"]), anchor="w", fill=GRIS, font=("Segoe UI", 10))
            p.texte(372, y, text="Course" if e.get("mode") == "course" else "Entraîn.",
                    anchor="w", fill=GRIS, font=("Segoe UI", 9))

        p.rect(460, 62, 870, 300, r=18, fill=CARTE, outline=BORD, width=2)
        p.texte(665, 85, text="Progression (20 dernières courses)", fill=BLANC, font=("Segoe UI", 12, "bold"))
        x0, x1, y0, y1 = 500, 850, 115, 270
        p.ligne(x0, y1, x1, y1, fill=GRIS)
        p.ligne(x0, y0, x0, y1, fill=GRIS)
        hist = [h["wpm"] for h in self.data["historique"][-20:]]
        if len(hist) >= 2:
            vmax = max(max(hist), 1)
            pts = []
            for i, v in enumerate(hist):
                pts += [x0 + i * (x1 - x0) / (len(hist) - 1), y1 - v / vmax * (y1 - y0)]
            p.ligne(*pts, fill=ACCENT, width=2)
            for i in range(0, len(pts), 2):
                p.oval(pts[i] - 3, pts[i + 1] - 3, pts[i] + 3, pts[i + 1] + 3, fill=BLANC)
            p.texte(x0 - 6, y0, text=str(vmax), anchor="e", fill=GRIS, font=("Segoe UI", 9))
            p.texte(x0 - 6, y1, text="0", anchor="e", fill=GRIS, font=("Segoe UI", 9))
        else:
            p.texte(665, 195, text="Joue au moins 2 courses", fill=GRIS, font=("Segoe UI", 11))

        p.rect(460, 315, 870, 545, r=18, fill=CARTE, outline=BORD, width=2)
        p.texte(665, 338, text="Tes lettres les plus difficiles", fill=BLANC, font=("Segoe UI", 12, "bold"))
        faibles = stockage.lettres_faibles(self.data, n=6, minimum=3)
        if not faibles:
            p.texte(665, 440, text="Pas encore assez de données", fill=GRIS, font=("Segoe UI", 11))
        for i, lettre in enumerate(faibles):
            erreurs, total = self.data["lettres"][lettre]
            taux = erreurs / total
            y = 375 + i * 27
            p.texte(490, y, text=lettre.upper(), fill=BLANC, font=("Consolas", 15, "bold"))
            p.rect(515, y - 8, 515 + 280, y + 8, r=8, fill=FOND)
            if taux > 0.03:
                p.rect(515, y - 8, 515 + 280 * min(1, taux), y + 8, r=8, fill=ROUGE)
            p.texte(805, y, text=f"{round(taux * 100)}%", anchor="w", fill=GRIS, font=("Segoe UI", 10))

    # ---- course
    def dessiner_course(self, now):
        p = self.p
        piste = PISTES[self.data["piste"]]
        t = self.t_actuel(now)
        wpm = self.wpm_actuel(t) if self.etat != "end" else self.wpm_actuel(self.t_fin)

        secousse = (0.0, 0.0)
        if now < self.err_until + 0.12:
            secousse = (random.uniform(-0.10, 0.10), random.uniform(-0.05, 0.05))
        self.scene.dessiner(
            piste, self.data["qualite"], self.z_aff, self.voitures_3d(), self.z_arrivee(),
            now, wpm if self.etat == "race" else 0, secousse,
            feux_vifs=(now - self.derniere_touche) < 0.4)

        # panneau de saisie (cache le bas de la scène)
        p.rect(0, HAUT_PANNEAU, W, H, fill=FOND)
        p.ligne(0, HAUT_PANNEAU, W, HAUT_PANNEAU, fill=ACCENT, width=2)

        self.part.dessiner(p)
        self.dessiner_hud(piste, t)
        self.dessiner_boite_texte(now, t)
        if self.etat in ("countdown", "race"):
            self.bouton(W - 120, 58, W - 16, 80, "✕  Quitter", lambda: self.simuler("Escape"), taille=9, r=8)

        if self.etat == "countdown":
            n = max(1, math.ceil(3 - (now - self.t0)))
            p.texte(W // 2 + 3, 218, text=str(n), fill="#000000", font=("Segoe UI", 90, "bold"))
            p.texte(W // 2, 215, text=str(n), fill=BLANC, font=("Segoe UI", 90, "bold"))
            p.texte(W // 2, 290, text="Prépare tes doigts !", fill=BLANC, font=("Segoe UI", 14, "bold"))
            if self.boss:
                p.texte(W // 2, 330, text=f"DUEL : toi contre {self.boss['nom']}  ({self.boss['style']})",
                        fill=JAUNE, font=("Segoe UI", 15, "bold"))
            elif self.comp:
                p.texte(W // 2, 330, text=f"{FORMATS[self.comp.format]['nom'].upper()} · {self.comp.titre_manche()} · "
                        f"{self.comp.nb} voitures · {fmt_duree(self.duree)}",
                        fill=JAUNE, font=("Segoe UI", 14, "bold"))
        elif self.etat == "end" and now - self.t_terminee > self.delai_fin():
            self.dessiner_fin()
        dessiner_arrivee(self, now)

    def delai_fin(self):
        """Temps laissé au drapeau à damier avant d'afficher le résultat."""
        return 2.4 if self.fin_type in ("arrivee", "survivant") else 1.0

    def classement(self):
        """Liste triée (nom, couleur, distance en caractères) du premier au dernier."""
        lignes = [("TOI", COULEURS[self.data["couleur"]]["hex"], float(self.idx))]
        for b in self.bots:
            lignes.append((b.nom, b.couleur, min(float(self.goal), b.pos)))
        lignes.sort(key=lambda e: -e[2])
        return lignes

    def lignes_classement(self):
        """Classement réduit pour le panneau : tout si ≤ 6 voitures, sinon le haut + ta position."""
        tout = [(i + 1, n, c) for i, (n, c, _d) in enumerate(self.classement())]
        if len(tout) <= 6:
            return tout
        moi = next(l for l in tout if l[1] == "TOI")
        if moi[0] <= 4:
            return tout[:5] + [(0, f"… {len(tout)} voitures", GRIS)]
        return tout[:4] + [(0, "…", GRIS), moi]

    def dessiner_hud(self, piste, t):
        p = self.p
        wpm = round(self.wpm_actuel(t))
        p.rect(16, 14, 140, 52, r=12, fill=HUD, outline=BORD, width=1)
        p.texte(78, 33, text=f"{wpm} WPM", fill=BLANC, font=("Segoe UI", 15, "bold"))
        rem = max(0, self.duree - t) if self.etat != "countdown" else self.duree
        p.rect(W - 172, 14, W - 16, 52, r=12, fill=HUD, outline=BORD, width=1)
        p.texte(W - 94, 33, text=fmt_chrono(rem), fill=BLANC, font=("Segoe UI", 15, "bold"))
        info = f"Erreurs : {self.erreurs}   |   Précision : {self.precision()}%"
        if self.mode == "entrainement":
            info += f"   |   Tours : {self.idx // self.goal}"
        p.texte(W // 2, 33, text=info, fill=piste["hud"], font=("Segoe UI", 11, "bold"))
        if self.boss or self.comp:
            p.rect(W // 2 - 190, 46, W // 2 + 190, 67, r=10, fill=HUD)
        if self.boss:
            p.texte(W // 2, 56, text=f"DUEL contre {self.boss['nom']}", fill=JAUNE, font=("Segoe UI", 10, "bold"))
        elif self.comp:
            if self.comp.format == "elim" and self.etat == "race":
                reste = max(0.0, self.comp.prochaine - t)
                dernier = self.classement()[-1][0] == "TOI"
                p.texte(W // 2, 56, text=f"💀 Prochaine élimination dans {fmt_chrono(reste)} · {len(self.bots) + 1} en piste"
                        + ("  ⚠ tu es dernier !" if dernier else ""),
                        fill=ROUGE if dernier else JAUNE, font=("Segoe UI", 10, "bold"))
            else:
                p.texte(W // 2, 56, text=f"{FORMATS[self.comp.format]['nom']} · {self.comp.titre_manche()}",
                        fill=JAUNE, font=("Segoe UI", 10, "bold"))

        if self.mode == "course":
            lignes = self.lignes_classement()
            p.rect(16, 60, 190, 60 + 22 * len(lignes) + 8, r=12, fill=HUD, outline=BORD, width=1)
            for i, (rang, nom, col) in enumerate(lignes):
                y = 74 + i * 22
                if rang == 0:
                    p.texte(30, y, text=nom, anchor="w", fill=GRIS, font=("Segoe UI", 10))
                    continue
                p.rect(24, y - 6, 36, y + 6, r=3, fill=col)
                p.texte(44, y, text=f"{rang}. {nom}", anchor="w",
                        fill=BLANC if nom == "TOI" else "#cbd5e1",
                        font=("Segoe UI", 10, "bold" if nom == "TOI" else "normal"))

    def dessiner_boite_texte(self, now, t):
        p = self.p
        # compteur de vitesse
        cx, cy, r = 75, 505, 50
        p.arc(cx - r, cy - r, cx + r, cy + r, start=0, extent=180, style="arc", outline=ACCENT, width=5)
        wpm = min(150, self.wpm_actuel(t))
        ang = math.radians(180 - wpm / 150 * 180)
        p.ligne(cx, cy, cx + (r - 8) * math.cos(ang), cy - (r - 8) * math.sin(ang), fill=ROUGE, width=3)
        p.oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=BLANC)
        kmh = int(wpm * 5 / 60 * M_PAR_CHAR * 3.6)
        p.texte(cx, cy + 20, text=f"{kmh} km/h", fill=GRIS, font=("Segoe UI", 9, "bold"))

        # zone de texte
        p.rect(150, 415, 880, 530, r=18, fill=CARTE, outline=ACCENT, width=2)
        if self.mode == "entrainement":
            indice = (f"Lettres à travailler : {', '.join(self.faibles)}" if self.faibles else "Entraînement libre")
        else:
            indice = "Tape le texte exactement — une erreur te bloque !"
        p.texte(515, 432, text=indice, fill=GRIS, font=("Segoe UI", 9))
        cw, cx0, cy0 = 20, 515, 478
        for i in range(self.idx - 17, self.idx + 18):
            if i < 0 or i >= len(self.cible):
                continue
            x = cx0 + (i - self.idx) * cw
            if i < self.idx:
                col = VERT
            elif i == self.idx:
                col = BLANC
                p.rect(x - cw // 2, cy0 - 20, x + cw // 2, cy0 + 20, r=6,
                       fill=ROUGE if now < self.err_until else "#3b5bdb")
            else:
                col = "#cbd5e1"
            p.texte(x, cy0, text=self.cible[i], fill=col, font=("Consolas", 22, "bold"))

    def dessiner_fin(self):
        p = self.p
        r = self.resultat
        p.rect(0, 0, W, H, fill="black", stipple="gray50")
        p.rect(180, 90, 720, 470, r=24, fill=CARTE, outline=ACCENT, width=3)
        if self.comp:
            p.texte(W // 2, 108, text=f"{FORMATS[self.comp.format]['nom']} · {self.comp.titre_manche()}",
                    fill=GRIS, font=("Segoe UI", 10, "bold"))
        if r["place"] is None:
            titre = "Entraînement terminé"
        elif r.get("boss"):
            nom = r["boss"]["nom"]
            titre = f"🏆  {nom} battu !" if r["place"] == 1 else f"{nom} t'a battu"
        elif self.fin_type == "elimine":
            titre = f"💀  Éliminé · {r['place']}e place"
        else:
            titre = {1: "🏆  1ère place !", 2: "🥈  2e place", 3: "🥉  3e place"}.get(
                r["place"], f"{r['place']}e place")
        p.texte(W // 2, 140, text=titre, fill=BLANC, font=("Segoe UI", 28, "bold"))
        place = r["place"]
        if place in (1, 2, 3) and not self.comp and not r.get("boss") and self.fin_type != "elimine":
            # podium : position + message, avec le trophée (1re place) ou la médaille (2e, 3e)
            couleur = schema.MEDAILLES[place][1]
            p.texte(W // 2, 167, text=schema.phrase_podium(place), fill=couleur, font=("Segoe UI", 11, "bold"))
            schema.dessiner_recompense(p, 252, 262, 0.52 if place == 1 else 0.62, place, time.time())
            p.texte(252, 326, text=schema.MEDAILLES[place][0], fill=couleur, font=("Segoe UI", 9, "bold"))
        p.texte(W // 2, 195, text=f"{r['wpm']} WPM", fill=ACCENT, font=("Segoe UI", 24, "bold"))
        if r["record"]:
            p.texte(W // 2, 228, text="★ NOUVEAU RECORD ★", fill=JAUNE, font=("Segoe UI", 12, "bold"))
        p.texte(W // 2, 258, text=f"Précision : {r['precision']}%   |   Erreurs : {r['erreurs']}",
                fill="#e2e8f0", font=("Segoe UI", 13))
        if r["precedent"] is None:
            p.texte(W // 2, 292, text="Première course dans ce mode !", fill=GRIS, font=("Segoe UI", 12))
        else:
            diff = r["wpm"] - r["precedent"]
            p.texte(W // 2, 292, text=f"Course précédente : {r['precedent']} WPM  ({diff:+d})",
                    fill=VERT if diff >= 0 else ROUGE, font=("Segoe UI", 12, "bold"))
        p.texte(W // 2, 325, text=f"+{r['xp']} XP", fill=JAUNE, font=("Segoe UI", 14, "bold"))
        if r.get("boss_premiere"):
            p.texte(W // 2, 352, text=f"★ Premier boss vaincu : bonus +{r['boss']['bonus_xp']} XP inclus ★",
                    fill=VERT, font=("Segoe UI", 12, "bold"))
        if r["niveau"]:
            msg = f"NIVEAU {r['niveau']} !"
            if r["debloque"]:
                msg += "\nDébloqué : " + ", ".join(r["debloque"])
            p.texte(W // 2, 392 if r.get("boss_premiere") else 380, text=msg, fill=JAUNE, justify="center",
                    width=480, font=("Segoe UI", 12, "bold"))
        if self.theorie_incomplete() and r["precision"] < 92 and not self.comp:
            p.texte(W // 2, 412, text=f"💡 Précision {r['precision']} % : le mode théorique (TAB dans le menu) "
                    "t'apprend à taper juste.", fill=JAUNE, font=("Segoe UI", 10, "bold"), width=500)
        if self.comp:
            rejouer, sortie = "CONTINUER  (ENTRÉE)", "ABANDONNER  (ÉCHAP)"
        elif r.get("boss"):
            rejouer, sortie = "REVANCHE  (ENTRÉE)", "LISTE DES BOSS  (ÉCHAP)"
        else:
            rejouer, sortie = "REJOUER  (ENTRÉE)", "MENU  (ÉCHAP)"
        self.bouton(205, 428, 440, 462, rejouer, lambda: self.simuler("Return"), fond=VERT_BOUTON, fg=BLANC,
                    taille=12, r=14)
        self.bouton(460, 428, 695, 462, sortie, lambda: self.simuler("Escape"), taille=12, r=14)
