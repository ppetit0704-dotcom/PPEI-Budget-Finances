# core/calculs.py
"""
@author      : Philippe PETIT
@version     : 1.0.0
@description : Calculs comptables M57 — PPEI-Budget&Finances

Mécaniques comptables M57 — Section Fonctionnement
====================================================

PRODUITS RÉELS (recettes de gestion courante) :
    70  — Produits des services, du domaine et ventes diverses
    73  — Impôts et taxes
    731 — Fiscalité locale (sous-chapitre de 73, ligne distincte dans l'export)
    74  — Dotations et participations
    75  — Autres produits de gestion courante
    013 — Atténuations de charges

CHARGES RÉELLES (dépenses de gestion courante) :
    011 — Charges à caractère général
    012 — Charges de personnel et frais assimilés
    014 — Atténuations de produits
    65  — Autres charges de gestion courante

MARGE BRUTE = PRODUITS_RÉELS - CHARGES_RÉELLES

CHARGES FINANCIÈRES ET EXCEPTIONNELLES :
    66  — Charges financières
    67  — Charges exceptionnelles (spécifiques)
    NB  : 68 (dotations provisions) exclu car non décaissable

PRODUITS FINANCIERS ET EXCEPTIONNELS :
    76  — Produits financiers
    77  — Produits exceptionnels (spécifiques)

ÉPARGNE BRUTE = MARGE_BRUTE - CHARGES_AUTRES + PRODUITS_AUTRES

REMBOURSEMENT CAPITAL DETTE :
    16  — Emprunts et dettes assimilées (section investissement)

ÉPARGNE NETTE = ÉPARGNE_BRUTE - REMBOURSEMENT_CAPITAL

REPORT N-1 :
    002 — Résultat de fonctionnement reporté

DISPONIBILITÉ = ÉPARGNE_NETTE + REPORT_N1
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Constantes — chapitres par famille
# ---------------------------------------------------------------------------

CHAP_PRODUITS_REELS   = ["70", "73", "731", "74", "75", "013"]
CHAP_CHARGES_REELLES  = ["011", "012", "014", "65"]
CHAP_CHARGES_AUTRES   = ["66", "67"]
CHAP_PRODUITS_AUTRES  = ["76", "77"]
CHAP_REMB_CAPITAL     = ["16"]
CHAP_REPORT_N1        = ["002"]

# Colonnes historiques : N courant + N-1 à N-5
ANNEES_COLS   = ["Réalisé", "Liquidé_N_1", "Liquidé_N_2", "Liquidé_N_3", "Liquidé_N_4", "Liquidé_N_5"]
ANNEES_LABELS = ["N", "N-1", "N-2", "N-3", "N-4", "N-5"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sommes_par_chapitre(df: pd.DataFrame, col: str = "Réalisé") -> dict:
    """
    Retourne un dictionnaire {code_chapitre: montant}
    pour la colonne demandée (Réalisé, Liquidé_N_1 … Liquidé_N_5).
    Le code est extrait de la forme '011 - Libellé' → '011'.
    """
    sommes = {}
    if col not in df.columns:
        return sommes
    for ch, data in df.groupby("Chapitre"):
        code = str(ch).split("-")[0].strip()
        sommes[code] = data[col].sum()
    return sommes


def _somme_chapitres(sommes: dict, codes: list) -> float:
    """Additionne les montants d'une liste de codes chapitres."""
    return sum(sommes.get(c, 0.0) for c in codes)


def _calcul_indicateurs(sommes: dict) -> dict:
    """
    Calcule tous les indicateurs à partir d'un dict de sommes par chapitre.
    Utilisé pour N et pour chaque année historique.
    """
    FONC_TOT_REC_REEL = _somme_chapitres(sommes, CHAP_PRODUITS_REELS)
    FONC_TOT_DEP_REEL = _somme_chapitres(sommes, CHAP_CHARGES_REELLES)
    MARGE_BRUTE       = FONC_TOT_REC_REEL - FONC_TOT_DEP_REEL
    CHARGES_AUTRES    = _somme_chapitres(sommes, CHAP_CHARGES_AUTRES)
    PRODUITS_AUTRES   = _somme_chapitres(sommes, CHAP_PRODUITS_AUTRES)
    FONC_TOT_DEP      = FONC_TOT_DEP_REEL + CHARGES_AUTRES
    FONC_TOT_REC      = FONC_TOT_REC_REEL + PRODUITS_AUTRES
    EPARGNE_BRUTE     = MARGE_BRUTE - CHARGES_AUTRES + PRODUITS_AUTRES
    REMB_CAPITAL      = _somme_chapitres(sommes, CHAP_REMB_CAPITAL)
    EPARGNE_NETTE     = EPARGNE_BRUTE - REMB_CAPITAL
    REPORT_N1         = _somme_chapitres(sommes, CHAP_REPORT_N1)
    DISPONIBILITE     = EPARGNE_NETTE + REPORT_N1

    return {
        "FONC_TOT_DEP_REEL" : FONC_TOT_DEP_REEL,
        "FONC_TOT_REC_REEL" : FONC_TOT_REC_REEL,
        "MARGE_BRUTE"       : MARGE_BRUTE,
        "CHARGES_AUTRES"    : CHARGES_AUTRES,
        "PRODUITS_AUTRES"   : PRODUITS_AUTRES,
        "FONC_TOT_DEP"      : FONC_TOT_DEP,
        "FONC_TOT_REC"      : FONC_TOT_REC,
        "EPARGNE_BRUTE"     : EPARGNE_BRUTE,
        "REMB_CAPITAL"      : REMB_CAPITAL,
        "EPARGNE_NETTE"     : EPARGNE_NETTE,
        "REPORT_N1"         : REPORT_N1,
        "DISPONIBILITE"     : DISPONIBILITE,
    }


# ---------------------------------------------------------------------------
# Calcul principal — année N
# ---------------------------------------------------------------------------

def calcul_autofinancement(df: pd.DataFrame, budget: str) -> dict:
    """
    Calcule les indicateurs d'autofinancement M57 pour un budget donné (année N).

    Retourne un dict avec tous les indicateurs + 'detail' (sommes brutes par chapitre).
    """
    df_budget = df[df["Libellé_budget"] == budget].copy()
    sommes    = _sommes_par_chapitre(df_budget, "Réalisé")
    result    = _calcul_indicateurs(sommes)
    result["detail"] = sommes
    return result


# ---------------------------------------------------------------------------
# Calcul historique — N à N-5
# ---------------------------------------------------------------------------

def calcul_historique(df: pd.DataFrame, budget: str) -> dict:
    """
    Calcule les indicateurs d'autofinancement pour chaque année disponible
    (N, N-1, N-2, N-3, N-4, N-5) en appliquant la même formule sur chaque colonne.

    Retourne un dict :
    {
        "labels"        : ["N", "N-1", ..., "N-5"],
        "MARGE_BRUTE"   : [val_N, val_N1, ...],
        "EPARGNE_BRUTE" : [...],
        "EPARGNE_NETTE" : [...],
        "PRODUITS_AUTRES": [...],
        "REPORT_N1"     : [...],
        "DISPONIBILITE" : [...],
    }
    """
    df_budget = df[df["Libellé_budget"] == budget].copy()

    labels_dispo = []
    series = {k: [] for k in [
        "MARGE_BRUTE", "EPARGNE_BRUTE", "EPARGNE_NETTE",
        "PRODUITS_AUTRES", "REPORT_N1", "DISPONIBILITE",
    ]}

    for col, label in zip(ANNEES_COLS, ANNEES_LABELS):
        if col not in df_budget.columns:
            continue
        sommes = _sommes_par_chapitre(df_budget, col)
        indic  = _calcul_indicateurs(sommes)
        labels_dispo.append(label)
        for k in series:
            series[k].append(indic[k])

    return {"labels": labels_dispo, **series}
