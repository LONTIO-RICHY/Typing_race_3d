"""Arrivée : drapeaux à damier qui ondulent + bandes à damier + bandeau de message."""

import math

from config import ACCENT, BLANC, H, JAUNE, ROUGE, VERT, W
from moteur3d import melanger


TEXTES = {
    "arrivee": ("🏁  ARRIVÉE !", JAUNE),
    "survivant": ("🏁  DERNIER SURVIVANT !", JAUNE),
    "elimine": ("💀  ÉLIMINÉ !", ROUGE),
    "temps": ("⏱  TEMPS ÉCOULÉ", ACCENT),
}


def _drapeau(p, mat_x, y, w, h, now, sens):
    """Drapeau à damier qui flotte. sens = +1 : il part du mât vers la droite, -1 : vers la gauche."""
    cols, lignes = 10, 5
    cw, ch = w / cols, h / lignes

    def onde(c):                      # ondulation : nulle au mât, forte au bout
        return math.sin(now * 7.0 - c * 0.7) * 6.0 * (c / cols)

    for c in range(cols):
        xa, xb = mat_x + sens * c * cw, mat_x + sens * (c + 1) * cw
        ya, yb = y + onde(c), y + onde(c + 1)
        ombre = min(0.4, abs(yb - ya) * 0.07)
        for r in range(lignes):
            base = "#121212" if (r + c) % 2 == 0 else "#f6f6f6"
            col = melanger(base, "#000000", ombre) if ya > yb else melanger(base, "#8a8f99", ombre * 0.6)
            p.poly([xa, ya + r * ch, xb, yb + r * ch, xb, yb + (r + 1) * ch, xa, ya + (r + 1) * ch], fill=col)
    p.rect(mat_x - 2.5, y - 8, mat_x + 2.5, y + h + 12, fill="#cbd5e1")      # mât
    p.oval(mat_x - 6, y - 15, mat_x + 6, y - 3, fill=JAUNE)


def _bande(p, y, hauteur, now, sens):
    """Bande à damier qui défile sur toute la largeur."""
    case = hauteur
    decalage = (now * 60 * sens) % (2 * case)
    x = -2 * case + decalage
    k = 0
    while x < W:
        p.rect(x, y, x + case, y + hauteur / 2, fill="#101010" if k % 2 == 0 else "#f6f6f6")
        p.rect(x, y + hauteur / 2, x + case, y + hauteur, fill="#f6f6f6" if k % 2 == 0 else "#101010")
        x += case
        k += 1


def _demi_largeur(texte, taille):
    return 22 + len(texte) * taille * 0.36


def _bandeau(p, texte, couleur, y, taille, ouverture):
    """Plaque sombre + texte : elle s'ouvre et descend en douceur."""
    ouverture = max(0.0, min(1.0, ouverture))
    glisse = (1 - ouverture) ** 2 * 40
    largeur = _demi_largeur(texte, taille) * (0.6 + 0.4 * ouverture)
    p.rect(W / 2 - largeur, y - 24 - glisse, W / 2 + largeur, y + 24 - glisse, r=14,
           fill="#050816", outline=couleur, width=2)
    p.texte(W / 2 + 2, y + 2 - glisse, text=texte, fill="#000000", font=("Segoe UI", taille, "bold"))
    p.texte(W / 2, y - glisse, text=texte, fill=couleur, font=("Segoe UI", taille, "bold"))


def dessiner_arrivee(jeu, now):
    """Dessine l'ambiance de fin de course par-dessus la scène (à appeler en dernier, après le panneau de fin)."""
    p = jeu.p
    if jeu.etat == "race":
        # entraînement : un petit drapeau à chaque tour bouclé
        if jeu.arrivee_t is not None and now - jeu.arrivee_t < 2.2:
            t = now - jeu.arrivee_t
            texte = f"🏁  TOUR {jeu.dernier_tour} !"
            d = _demi_largeur(texte, 22) + 6
            _drapeau(p, W / 2 - d, 14, 90 * min(1, t * 4), 46, now, -1)
            _drapeau(p, W / 2 + d, 14, 90 * min(1, t * 4), 46, now, 1)
            _bandeau(p, texte, VERT, 66, 22, t * 4)
        return
    if jeu.etat != "end" or not jeu.fin_type:
        return
    t_fin = now - jeu.t_terminee
    victoire = jeu.fin_type in ("arrivee", "survivant")
    couleur_bandes = {"elimine": ROUGE}.get(jeu.fin_type, None)

    # bandes à damier en haut et en bas de la fenêtre
    ouverture = min(1.0, t_fin * 3)
    if ouverture > 0:
        h = 14 * ouverture
        _bande(p, 0, h, now, 1)
        _bande(p, H - h, h, now, -1)
        if couleur_bandes:
            p.rect(0, h, W, h + 4, fill=couleur_bandes)
            p.rect(0, H - h - 4, W, H - h, fill=couleur_bandes)

    # drapeaux : dès que la voiture franchit la ligne (ou tout de suite pour un survivant)
    if victoire and jeu.arrivee_t is not None:
        t = now - jeu.arrivee_t
        croissance = min(1.0, t * 3)
        d = _demi_largeur(TEXTES.get(jeu.fin_type, ("", ""))[0], 24) + 6
        _drapeau(p, W / 2 - d, 14, 105 * croissance, 48, now, -1)
        _drapeau(p, W / 2 + d, 14, 105 * croissance, 48, now, 1)

    texte, couleur = TEXTES.get(jeu.fin_type, ("🏁  COURSE TERMINÉE", BLANC))
    if victoire and jeu.arrivee_t is None:
        return                              # le message attend que la voiture passe la ligne
    _bandeau(p, texte, couleur, 66, 24, (now - (jeu.arrivee_t or jeu.t_terminee)) * 4)
