"""Sauvegarde : scores, niveau, statistiques, personnalisation."""

import copy
import json
import os
from datetime import datetime
from pathlib import Path

from chemins import dossier_donnees
from clavier import ORDRE
from config import (COULEURS, DUREE_MAX, DUREE_MIN, MODELES, NB_NIVEAUX_THEORIE,
                    NIVEAU_MAX, PISTES, SEUIL_THEORIE, XP_PAR_NIVEAU)

FICHIER = dossier_donnees() / "typing_race_donnees.json"

DEFAUT = {
    "xp": 0,
    "meilleur": 0,
    "top": [],          # 10 meilleurs scores
    "historique": [],   # 50 dernières courses
    "lettres": {},      # lettre -> [erreurs, total]
    "modele": 0,
    "couleur": 0,
    "piste": 0,
    "muet": False,
    "musique": "",       # nom du fichier choisi
    "volume": 0.6,
    "qualite": 2,       # 1 = légère, 2 = normale, 3 = élevée
    "clavier": "",      # disposition choisie (azerty, qwerty...)
    "theorie": {},      # progression du mode théorique, par disposition
    "guide_doigts": True,
    "boss_vaincus": [],  # identifiants des boss déjà battus
    "duree": 30,        # durée de course choisie (secondes, saisie libre possible)
    "trophees": [],     # résultats des compétitions (30 derniers)
}


def _valide(data):
    """Remet à sa valeur par défaut tout champ de type invalide (fichier abîmé ou modifié à la main)."""
    for cle, defaut in DEFAUT.items():
        val = data.get(cle)
        attendu = type(defaut)
        if attendu is float:
            ok = isinstance(val, (int, float)) and not isinstance(val, bool)
        elif attendu is int:
            ok = isinstance(val, int) and not isinstance(val, bool)
        else:
            ok = isinstance(val, attendu)
        if not ok:
            data[cle] = copy.deepcopy(defaut)
    for cle, liste in (("modele", MODELES), ("couleur", COULEURS), ("piste", PISTES)):
        if not 0 <= data[cle] < len(liste):
            data[cle] = 0
    if data["qualite"] not in (1, 2, 3):
        data["qualite"] = 2
    data["volume"] = round(max(0.0, min(1.0, float(data["volume"]))), 1)
    data["xp"] = max(0, data["xp"])
    data["duree"] = max(DUREE_MIN, min(DUREE_MAX, data["duree"]))
    if data["clavier"] and data["clavier"] not in ORDRE:     # disposition inconnue (fichier modifié à la main)
        data["clavier"] = ""
    data["trophees"] = [t for t in data["trophees"]
                        if isinstance(t, dict) and isinstance(t.get("format"), str)
                        and isinstance(t.get("n"), int)][-30:]
    # listes d'entrées : on garde seulement les dictionnaires bien formés
    for cle in ("top", "historique"):
        data[cle] = [e for e in data[cle]
                     if isinstance(e, dict) and isinstance(e.get("wpm"), (int, float))
                     and isinstance(e.get("precision", 0), (int, float))
                     and isinstance(e.get("duree", 0), (int, float))]
    data["boss_vaincus"] = sorted({b for b in data["boss_vaincus"] if isinstance(b, str)})
    data["lettres"] = {k: v for k, v in data["lettres"].items()
                       if isinstance(v, list) and len(v) == 2
                       and all(isinstance(n, int) for n in v)}
    data["theorie"] = {k: v for k, v in data["theorie"].items()
                       if isinstance(v, dict) and isinstance(v.get("scores"), dict)
                       and isinstance(v.get("debloque"), int)}
    return data


def charger():
    data = copy.deepcopy(DEFAUT)
    try:
        with open(FICHIER, encoding="utf-8") as f:
            lu = json.load(f)
        if isinstance(lu, dict):
            data.update(lu)
        else:
            raise ValueError("format inattendu")
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        # fichier illisible : on le met de côté au lieu de l'écraser (progression récupérable à la main)
        try:
            os.replace(FICHIER, FICHIER.with_suffix(".corrompu.json"))
        except OSError:
            pass
    return _valide(data)


def sauver(data):
    """Écriture atomique : fichier temporaire puis remplacement, pour ne jamais laisser un JSON à moitié écrit."""
    tmp = FICHIER.with_suffix(".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, FICHIER)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def niveau_de(xp):
    return min(NIVEAU_MAX, 1 + xp // XP_PAR_NIVEAU)


def xp_dans_niveau(xp):
    return xp % XP_PAR_NIVEAU


def deblocages(ancien, nouveau):
    """Liste des éléments débloqués en passant de 'ancien' à 'nouveau'."""
    noms = []
    for titre, liste in (("Modèle", MODELES), ("Couleur", COULEURS), ("Piste", PISTES)):
        for it in liste:
            if ancien < it["niveau"] <= nouveau:
                noms.append(f"{titre} {it['nom']}")
    return noms


def lettres_faibles(data, n=5, minimum=8):
    """Lettres avec le plus fort taux d'erreur (au moins 'minimum' essais)."""
    scores = []
    for lettre, (erreurs, total) in data["lettres"].items():
        if total >= minimum and erreurs > 0:
            scores.append((erreurs / total, lettre))
    scores.sort(reverse=True)
    return [lettre for _, lettre in scores[:n]]


def enregistrer(data, entree, lettres, xp):
    entree["date"] = datetime.now().strftime("%d/%m")
    data["historique"].append(entree)
    data["historique"] = data["historique"][-50:]
    data["top"].append(entree)
    data["top"].sort(key=lambda e: e["wpm"], reverse=True)
    data["top"] = data["top"][:10]
    data["meilleur"] = max(data["meilleur"], entree["wpm"])
    data["xp"] += xp
    fusionner_lettres(data, lettres)
    sauver(data)


def fusionner_lettres(data, lettres):
    for lettre, (erreurs, total) in lettres.items():
        ancien = data["lettres"].get(lettre, [0, 0])
        data["lettres"][lettre] = [ancien[0] + erreurs, ancien[1] + total]


# ------------------------------------------------------------ mode théorique
def progression_theorie(data, layout):
    return data["theorie"].setdefault(layout, {"debloque": 1, "scores": {}})


def niveaux_reussis(data):
    """Nombre de niveaux théoriques réussis sur le clavier choisi."""
    layout = data.get("clavier")
    if not layout:
        return 0
    scores = data["theorie"].get(layout, {}).get("scores", {})
    return sum(1 for s in scores.values() if s.get("reussi"))


def enregistrer_theorie(data, layout, niveau, wpm, precision, lettres):
    """Enregistre un niveau théorique. Retourne un dict de résultats."""
    prog = progression_theorie(data, layout)
    reussi = precision >= SEUIL_THEORIE
    etoiles = 3 if precision >= 97 else 2 if precision >= 92 else 1 if reussi else 0
    cle = str(niveau)
    ancien = prog["scores"].get(cle)
    premiere_reussite = reussi and not (ancien and ancien.get("reussi"))
    meilleur = {"wpm": wpm, "precision": precision, "etoiles": etoiles, "reussi": reussi}
    if ancien:
        if (ancien.get("etoiles", 0), ancien.get("wpm", 0)) > (etoiles, wpm):
            meilleur = dict(ancien, reussi=ancien.get("reussi") or reussi)
        else:
            meilleur["reussi"] = reussi or ancien.get("reussi", False)
    prog["scores"][cle] = meilleur
    if reussi and niveau == prog["debloque"] and niveau < NB_NIVEAUX_THEORIE:
        prog["debloque"] = niveau + 1
    xp = (25 if premiere_reussite else 10) if reussi else 0
    data["xp"] += xp
    fusionner_lettres(data, lettres)
    sauver(data)
    return {"reussi": reussi, "etoiles": etoiles, "xp": xp, "premiere": premiere_reussite}
