# core/data_loader.py
"""
Chargement, détection d'encodage/séparateur et nettoyage des CSV
Situation comptable + Grand Livre M57
"""

import pandas as pd
import chardet
import re
import streamlit as st

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_encoding(path: str) -> str:
    """Détecte l'encodage d'un fichier binaire."""
    with open(path, "rb") as f:
        raw = f.read(8192)
    result = chardet.detect(raw)
    enc = result.get("encoding", "utf-8") or "utf-8"
    # BOM UTF-8 → utf-8-sig pour que pandas retire le BOM
    if enc.lower() in ("utf-8-sig", "utf-8-bom"):
        return "utf-8-sig"
    if enc.lower().startswith("utf-8"):
        # Vérifier la présence du BOM manuellement
        if raw[:3] == b'\xef\xbb\xbf':
            return "utf-8-sig"
        return "utf-8"
    return enc


def _detect_separator(path: str, encoding: str) -> str:
    """Détecte le séparateur de champs parmi ; , \\t |"""
    with open(path, "r", encoding=encoding, errors="replace") as f:
        head = f.readline()
    counts = {sep: head.count(sep) for sep in [";", ",", "\t", "|"]}
    return max(counts, key=counts.get)


def _fr_to_float(series: pd.Series) -> pd.Series:
    """Convertit des nombres FR (virgule décimale, espace milliers) en float."""
    return (
        series.astype(str)
        .str.replace("\u202f", "", regex=False)   # espace fine insécable
        .str.replace("\xa0", "", regex=False)      # espace insécable
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )


# ---------------------------------------------------------------------------
# Chargement Situation
# ---------------------------------------------------------------------------

COLS_NUM_SIT = [
    "Total_Prévu", "Réalisé", "__Réalisé_", "Disponible__réalisé_",
    "__Dispo__réalisé_", "Liquidé_N_1", "Liquidé_N_2", "Liquidé_N_3",
    "Liquidé_N_4", "Liquidé_N_5", "Dégagé", "Engagé", "Reste_engagé",
]


def load_situation(path: str) -> pd.DataFrame:
    """Charge et nettoie la situation comptable."""
    enc = _detect_encoding(path)
    sep = _detect_separator(path, enc)
    df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Conversion colonnes numériques
    for col in COLS_NUM_SIT:
        if col in df.columns:
            df[col] = _fr_to_float(df[col])

    # Nettoyage chaînes
    for col in ["Sens", "Section", "Chapitre", "Libellé_budget", "Compte"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


# ---------------------------------------------------------------------------
# Chargement Grand Livre
# ---------------------------------------------------------------------------

COLS_FLOAT_GL = [
    "Total__R_V_", "Engagé", "Dégagé", "Liquidé",
    "Montant_HT", "Montant_TVA_récupérable", "Montant_TTC",
    "Réalisé", "Reste_engagé",
]


def load_grand_livre(path: str) -> pd.DataFrame:
    """Charge et nettoie le grand livre."""
    enc = _detect_encoding(path)
    sep = _detect_separator(path, enc)
    df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Colonnes float
    for col in COLS_FLOAT_GL:
        if col in df.columns:
            df[col] = _fr_to_float(df[col])

    # Exercice
    if "Exercice" in df.columns:
        df["Exercice"] = pd.to_numeric(df["Exercice"], errors="coerce")

    # Date
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    # Nettoyage chaînes
    for col in ["Sens", "Section", "Chapitre", "Libellé_budget",
                "Compte", "type", "Objet", "Tiers", "Imputation",
                "Réel_Ordre", "N_Bordereau", "N_Pièce", "N_Engagement"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", "")

    # Supprimer lignes sans Sens (totaux automatiques)
    df = df[df["Sens"].isin(["D", "R"])].copy()

    return df


# ---------------------------------------------------------------------------
# Cache Streamlit
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def get_situation(path: str) -> pd.DataFrame:
    return load_situation(path)


@st.cache_data(show_spinner=False)
def get_grand_livre(path: str) -> pd.DataFrame:
    return load_grand_livre(path)
