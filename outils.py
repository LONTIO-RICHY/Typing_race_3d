"""Petits outils : affichage et saisie des durées (de quelques secondes à plusieurs jours)."""

import re

_UNITES = {
    "s": ("s", 1), "sec": ("s", 1), "secs": ("s", 1), "seconde": ("s", 1), "secondes": ("s", 1),
    "m": ("m", 60), "mn": ("m", 60), "min": ("m", 60), "mins": ("m", 60),
    "minute": ("m", 60), "minutes": ("m", 60),
    "h": ("h", 3600), "heure": ("h", 3600), "heures": ("h", 3600),
    "j": ("j", 86400), "d": ("j", 86400), "jour": ("j", 86400), "jours": ("j", 86400),
}
_MOTIF = re.compile(r"\s*(\d+(?:\.\d+)?)\s*([a-z]*)\s*")


def fmt_duree(secondes):
    """45 -> '45 s' ; 90 -> '1 min 30 s' ; 3600 -> '1 h' ; 86400 -> '24 h' ; 3 jours -> '3 j'."""
    s = int(round(secondes))
    j, reste = divmod(s, 86400) if s >= 2 * 86400 else (0, s)       # « 24 h » plutôt que « 1 j » jusqu'à 47 h
    h, reste = divmod(reste, 3600)
    m, sec = divmod(reste, 60)
    morceaux = [f"{v} {u}" for v, u in ((j, "j"), (h, "h"), (m, "min"), (sec, "s")) if v]
    return " ".join(morceaux[:3]) if morceaux else "0 s"


def fmt_chrono(secondes):
    """Compte à rebours : '0:42.3' sous une heure, '3:25:07' au-delà (jusqu'à plusieurs centaines d'heures)."""
    secondes = max(0.0, secondes)
    if secondes >= 3600:
        total = int(secondes)
        return f"{total // 3600}:{total % 3600 // 60:02d}:{total % 60:02d}"
    return f"{int(secondes // 60)}:{secondes % 60:04.1f}"


def parse_duree(texte):
    """Lit une durée écrite à la main. Retourne des secondes (int) ou None si illisible.

    Exemples : 90 (secondes) | 5 min | 2h | 1h30 | 1j | 3 jours | 1:30:00 | 2:15 (min:s)
    """
    t = (texte or "").strip().lower().replace(",", ".")
    if not t:
        return None
    if re.fullmatch(r"\d+(:\d{1,2}){1,2}", t):
        p = [int(x) for x in t.split(":")]
        total = p[0] * 60 + p[1] if len(p) == 2 else p[0] * 3600 + p[1] * 60 + p[2]
        return total or None
    total, pos, dernier = 0.0, 0, None
    while pos < len(t):
        m = _MOTIF.match(t, pos)
        if not m or m.end() == pos:
            return None
        nombre, unite = float(m.group(1)), m.group(2)
        if unite:
            if unite not in _UNITES:
                return None
            dernier, mult = _UNITES[unite]
        else:
            # nombre sans unité : « 1h30 » = 30 minutes, « 2min30 » = 30 secondes, sinon des secondes
            mult = {"j": 3600, "h": 60}.get(dernier, 1)
            dernier = {"j": "h", "h": "m"}.get(dernier, "s")
        total += nombre * mult
        pos = m.end()
    total = int(round(total))
    return total if total > 0 else None
