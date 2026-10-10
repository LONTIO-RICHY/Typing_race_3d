"""Réglages et données fixes du jeu."""

W, H = 900, 560

# Signature du créateur : affichée dans le jeu (accueil + écran Contact), dans erreurs.log et le LISEZ-MOI
AUTEUR = {
    "nom": "LONTIO KESSEL",
    "whatsapp": "+237 650 196 251",
    "whatsapp_lien": "https://wa.me/237650196251",
    "email": "lontiokessel@gmail.com",
    "github": "https://github.com/LONTIo-RICHY",
}
HAUT_PANNEAU = 408            # le panneau de saisie commence ici
M_PAR_CHAR = 3.0              # 1 caractère tapé = 3 mètres parcourus
DEMI_ROUTE = 6.0              # demi-largeur de la route (mètres)
VOIES_X = [-4.5, -1.5, 1.5, 4.5]
VOIE_JOUEUR = 1               # la voiture du joueur roule sur la 2e voie

CHARS_PAR_SECONDE = 6         # distance de la course = durée x 6 caractères
TOUR_ENTRAINEMENT = 100       # longueur d'un "tour" en mode entraînement
DUREES = [15, 30, 60, 120, 300, 900, 3600, 86400]    # secondes (choix rapides)
XP_PAR_NIVEAU = 200
NIVEAU_MAX = 10
NB_NIVEAUX_THEORIE = 6        # niveaux du mode théorique
SEUIL_THEORIE = 85            # précision (%) minimale pour réussir un niveau

# Couleurs de l'interface (indigo profond, cyan électrique, violet, ambre)
FOND = "#070b1f"
FOND2 = "#131a4a"            # bas du dégradé des menus
CARTE = "#111a3b"
CARTE_HAUT = "#1b2860"       # carte survolée / sélectionnée
BORD = "#2b3a78"
ACCENT = "#22d3ee"
ACCENT2 = "#a78bfa"
VERT = "#34d399"
ROUGE = "#fb7185"
JAUNE = "#fbbf24"
GRIS = "#94a3b8"
BLANC = "#f8fafc"
VERT_BOUTON = "#10b981"
HUD = "#0a1030"              # fond des petits panneaux du jeu

# Durée d'une course : valeurs proposées dans la liste, mais l'utilisateur peut saisir ce qu'il veut
DUREE_MIN = 5                      # secondes
DUREE_MAX = 30 * 24 * 3600         # 30 jours

# Souris : False = la liste déroulante s'ouvre seulement au clic (True = dès que le curseur passe dessus)
OUVRIR_AU_SURVOL = False

# Vitesse des adversaires (mots/minute) selon la difficulté
DIFFICULTES = {
    "1": ("Facile", [25, 35, 45]),
    "2": ("Normal", [40, 55, 70]),
    "3": ("Difficile", [55, 75, 95]),
}

# Boss : duels 1 contre 1 (toi + le boss = 2 places). Chaque boss se débloque à un niveau du joueur.
#   wpm        : vitesse moyenne visée (mots/minute)
#   p_erreur   : chance, à chaque phase, de faire une faute (il ralentit)
#   p_rafale   : chance de partir en rafale (il accélère)
#   rattrapage : bonus de vitesse quand tu es devant lui (il s'accroche)
#   depart     : multiplicateur de vitesse au départ (diminue en 4 s)   final : dans le dernier quart
#   bonus_xp   : XP en plus la PREMIÈRE fois qu'on le bat
BOSSES = [
    {"id": "rapido", "nom": "Rapido", "niveau": 3, "wpm": 42, "couleur": "#d946ef", "modele": 0,
     "style": "Impulsif", "desc": "Part comme une fusée, mais fait beaucoup de fautes.",
     "p_erreur": 0.30, "p_rafale": 0.30, "rattrapage": 0.0, "depart": 1.4, "final": 0.9, "bonus_xp": 100},
    {"id": "max", "nom": "Mécano Max", "niveau": 5, "wpm": 58, "couleur": "#0ea5a4", "modele": 2,
     "style": "Régulier", "desc": "Presque jamais de faute : un rythme de métronome.",
     "p_erreur": 0.04, "p_rafale": 0.08, "rattrapage": 0.10, "depart": 1.0, "final": 1.0, "bonus_xp": 150},
    {"id": "comete", "nom": "La Comète", "niveau": 7, "wpm": 72, "couleur": "#f97316", "modele": 1,
     "style": "Rageur", "desc": "Des rafales, et il s'accroche si tu passes devant.",
     "p_erreur": 0.14, "p_rafale": 0.30, "rattrapage": 0.22, "depart": 1.25, "final": 1.05, "bonus_xp": 200},
    {"id": "champion", "nom": "Le Champion", "niveau": 10, "wpm": 88, "couleur": "#eab308", "modele": 1,
     "style": "Impitoyable", "desc": "Quasi sans faute, il accélère à la fin.",
     "p_erreur": 0.03, "p_rafale": 0.14, "rattrapage": 0.30, "depart": 1.0, "final": 1.10, "bonus_xp": 300},
]

# (nom, couleur, modèle de voiture)
BOTS = [
    ("ProTypist", "#2457c5", 1),
    ("SpeedBot", "#1f9d55", 0),
    ("Rookie", "#e8eaed", 2),
]

MODELES = [
    {"nom": "Citadine", "niveau": 1},
    {"nom": "Sportive", "niveau": 3},
    {"nom": "Pick-up", "niveau": 6},
]

COULEURS = [
    {"nom": "Rouge", "hex": "#c8102e", "niveau": 1},
    {"nom": "Bleu", "hex": "#1f5fd6", "niveau": 1},
    {"nom": "Jaune", "hex": "#f4b400", "niveau": 2},
    {"nom": "Vert", "hex": "#169c57", "niveau": 3},
    {"nom": "Violet", "hex": "#7b3fe4", "niveau": 4},
    {"nom": "Orange", "hex": "#f26a1b", "niveau": 5},
    {"nom": "Argent", "hex": "#b9c0c9", "niveau": 7},
    {"nom": "Noir", "hex": "#1a1b1f", "niveau": 8},
]

# Pistes 3D : ciel (haut, horizon), herbe/route (2 teintes qui alternent),
# montagnes (3 plans), décor (objets 3D le long de la route)
PISTES = [
    {"nom": "Campagne", "niveau": 1,
     "ciel": ("#2f7fd0", "#c4e4f6"), "brume": "#cfe6f2",
     "herbe": ("#4f9d3a", "#478f33"), "route": ("#5a5e65", "#54585f"),
     "montagnes": ["#a9bfd3", "#86a898", "#5d8d52"],
     "deco": ["arbre", "arbre2", "arbre", "meule"],
     "soleil": ("#fff6c8", 0.72), "hud": "#0b1d3a",
     "lumiere": (-0.45, 0.65, 0.35), "ambiant": 0.46, "diffus": 0.66},
    {"nom": "Ville", "niveau": 2,
     "ciel": ("#4f8bc7", "#dbe7f1"), "brume": "#d4e0ea",
     "herbe": ("#8a8f96", "#82878e"), "route": ("#4a4d53", "#45484e"),
     "montagnes": ["#b6c4d2", "#9dacbb", "#7f8e9d"],
     "deco": ["immeuble", "immeuble", "arbre", "immeuble"],
     "soleil": ("#fff3c4", 0.30), "hud": "#0b1d3a",
     "lumiere": (-0.45, 0.65, 0.35), "ambiant": 0.46, "diffus": 0.66},
    {"nom": "Désert", "niveau": 3,
     "ciel": ("#e8914a", "#fbdca6"), "brume": "#f3d29f",
     "herbe": ("#d9a867", "#d1a05f"), "route": ("#6e5f55", "#675850"),
     "montagnes": ["#dca172", "#c4835a", "#a8683f"],
     "deco": ["cactus", "rocher", "cactus", "rocher"],
     "soleil": ("#fff1c9", 0.28), "hud": "#4a2c0b",
     "lumiere": (-0.5, 0.55, 0.45), "ambiant": 0.5, "diffus": 0.7},
    {"nom": "Nuit", "niveau": 5,
     "ciel": ("#040815", "#22305c"), "brume": "#1a2447",
     "herbe": ("#14301f", "#112a1b"), "route": ("#2c2f36", "#282b32"),
     "montagnes": ["#18223f", "#121b34", "#0b1226"],
     "deco": ["lampadaire", "arbre", "immeuble", "lampadaire"],
     "lune": 0.70, "etoiles": True, "hud": "#e2e8f0",
     "lumiere": (-0.3, 0.55, 0.4), "ambiant": 0.30, "diffus": 0.40,
     "teinte": (0.72, 0.82, 1.15), "nuit": True},
    {"nom": "Neige", "niveau": 7,
     "ciel": ("#86aed6", "#eef5fb"), "brume": "#e6eef6",
     "herbe": ("#f1f6fa", "#e3ecf3"), "route": ("#6d7178", "#686c73"),
     "montagnes": ["#d3deeb", "#b7c9dd", "#9db3cc"],
     "deco": ["sapin_neige", "sapin_neige", "rocher_neige", "sapin_neige"],
     "soleil": ("#ffffff", 0.66), "hud": "#1e3a5f",
     "lumiere": (-0.45, 0.65, 0.35), "ambiant": 0.52, "diffus": 0.62},
]

# Mots (sans accents pour l'instant)
MOTS = {
    "fr": ("Français", """
        vitesse course voiture moteur piste rapide doigts clavier
        victoire depart arrivee virage route pilote essence lumiere
        ordinateur programme python projet bonjour soleil montagne
        chemin travail jouer gagner perdre enfant maison village
        fenetre musique cadeau reponse question lecture ecriture
        ligne nombre liberte avenir courage energie signal reseau
    """.split()),
    "en": ("English", """
        speed race car engine track fast fingers keyboard victory
        start finish corner road driver fuel light computer program
        python project hello sun mountain path work play win lose
        window music gift answer question reading writing line
        number freedom future courage energy signal network force
        actually really always never thunder bridge golden silver
    """.split()),
}
