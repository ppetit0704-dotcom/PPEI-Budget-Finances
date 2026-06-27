# core/saisie.py
"""
@author      : Philippe PETIT
@version     : 2.0.0
@description : Gestion de la saisie manuelle des données complémentaires
               Bilan comptable + Fiscalité + Dette
               Persistance en st.session_state
"""

import streamlit as st

# ---------------------------------------------------------------------------
# Clés session_state — préfixe "saisie_"
# ---------------------------------------------------------------------------

# Structure : {budget_label: {champ: valeur}}
SESSION_KEY = "saisie_complementaire"


def _init_session():
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = {}


def _get_budget_data(budget: str) -> dict:
    _init_session()
    if budget not in st.session_state[SESSION_KEY]:
        st.session_state[SESSION_KEY][budget] = {}
    return st.session_state[SESSION_KEY][budget]


def get_valeur(budget: str, champ: str, defaut: float = 0.0) -> float:
    """Retourne la valeur saisie pour un budget et un champ donné."""
    d = _get_budget_data(budget)
    return float(d.get(champ, defaut))


def set_valeur(budget: str, champ: str, valeur: float):
    """Enregistre une valeur dans la session."""
    d = _get_budget_data(budget)
    d[champ] = valeur


def reset_budget(budget: str):
    """Réinitialise toutes les saisies d'un budget."""
    _init_session()
    st.session_state[SESSION_KEY][budget] = {}


def est_complet(budget: str, champs_requis: list) -> bool:
    """Retourne True si tous les champs requis sont non nuls."""
    return all(get_valeur(budget, c) > 0 for c in champs_requis)


def get_all(budget: str) -> dict:
    """Retourne toutes les valeurs saisies pour un budget."""
    return dict(_get_budget_data(budget))


# ---------------------------------------------------------------------------
# Groupes de champs — définition métier
# ---------------------------------------------------------------------------

CHAMPS_BILAN = [
    # (clé, libellé, aide, compte M57)
    # ⚠️ Les immobilisations brutes flux N (20+21+23), subventions (13), dotations (10+14)
    # sont auto-calculées depuis la situation comptable.
    # Seules les données de STOCK (bilan cumulé) nécessitent une saisie manuelle.
    ("amortissements",  "Amortissements cumulés (bilan)",   "Cumul total des amortissements au 31/12 — compte de bilan",   "28"),
    ("provisions",      "Provisions (bilan)",               "Provisions pour risques et charges au 31/12",                 "15"),
    ("fonds_propres",   "Fonds propres cumulés",            "Capitaux propres + réserves + résultats cumulés au 31/12",    "10 cumulé"),
    ("actifs_circ",     "Actifs circulants",                "Créances clients, stocks, autres actifs courants au 31/12",   "41 + 45"),
    ("dettes_ct",       "Dettes court terme",               "Fournisseurs, dettes fiscales et sociales, autres dettes CT", "40 + 42 + 43"),
]

CHAMPS_FISCALITE = [
    # ⚠️ Le produit fiscal N-1 est auto-calculé depuis Liquidé_N_1 (chap. 73+731).
    # Seules les bases d'imposition nécessitent une saisie (source : notification DGFIP).
    ("bases_th",        "Bases TH / résidences secondaires",        "Bases nettes d'imposition TH (si applicable)",        "TH"),
    ("bases_tf",        "Bases taxe foncière bâti",                 "Bases nettes d'imposition TFB",                       "TFB"),
    ("bases_tfnb",      "Bases taxe foncière non bâti",             "Bases nettes d'imposition TFNB",                      "TFNB"),
    ("bases_cfe",       "Bases CFE",                                "Bases nettes d'imposition CFE",                       "CFE"),
    # Optionnel : saisir si la valeur auto (Liquidé_N_1 chap.73) est incorrecte
    ("bases_n1_fiscal", "Produit fiscal N-1 (override)",            "Laisser à 0 pour utiliser la valeur auto Liquidé_N_1","73 N-1"),
]

CHAMPS_DETTE = [
    ("encours_reel",    "Encours réel de la dette",         "Capital restant dû au 31/12 (état de la dette)",             "16"),
    ("emprunts_nv",     "Emprunts nouveaux de l'année",     "Nouveaux emprunts contractés sur l'exercice",                "1641"),
    ("annuite_totale",  "Annuité totale de la dette",       "Capital remboursé + intérêts payés sur l'exercice",          "16 + 661"),
]

TOUS_CHAMPS = CHAMPS_BILAN + CHAMPS_FISCALITE + CHAMPS_DETTE
