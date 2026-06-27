# core/ratios.py
"""
@author      : Philippe PETIT
@version     : 1.0.0
@description : Calcul des ratios M57 — PPEI-Budget&Finances

Chapitres utilisés (disponibles dans la Situation) :
  F/D : 011, 012, 014, 65, 66, 67, 68
  F/R : 013, 70, 73, 731, 74, 75, 76, 77
  I/D : 16, 20, 204, 21, 23, 27
  I/R : 10, 13

Données non disponibles (bilan) :
  - Immobilisations nettes, amortissements (2.3 / 4.2)
  - Fonds de roulement / BFR / Trésorerie nette (3.1)
  → affichées avec statut NA
"""

import pandas as pd
from core.saisie import get_valeur

NA = None   # Marqueur données non disponibles


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _s(sommes: dict, codes: list) -> float:
    """Somme des chapitres demandés."""
    return sum(sommes.get(c, 0.0) for c in codes)


def _pct(num: float, den: float) -> float | None:
    return round(num / den * 100, 2) if den else NA


def _ratio(num: float, den: float, decimales: int = 2) -> float | None:
    return round(num / den, decimales) if den else NA


def _build_sommes(df: pd.DataFrame) -> dict:
    """
    Construit un dict {code: valeur} à partir d'un DataFrame budget.
    Gère les codes à 2, 3 chiffres et les libellés '011 - Libellé'.
    """
    sommes = {}
    for ch, data in df.groupby("Chapitre"):
        code = str(ch).split("-")[0].strip()
        sommes[code] = sommes.get(code, 0.0) + data["Réalisé"].sum()
    return sommes


# ---------------------------------------------------------------------------
# Calcul principal
# ---------------------------------------------------------------------------

def calcul_ratios(
    df: pd.DataFrame,
    budget_label: str,
    population: int,
    nb_menages: int,
    nb_emplois: int,
    with_saisie: bool = True,
) -> dict:
    """
    Calcule l'ensemble des ratios M57 pour un budget donné.

    Retourne un dict structuré par groupe :
      epargne, endettement, investissement, structure,
      fiscalite, patrimoine, tresorerie, performance,
      premium, par_habitant, par_menage, par_emploi
    """
    df_b = df[df["Libellé_budget"] == budget_label].copy()
    s = _build_sommes(df_b)

    # -----------------------------------------------------------------------
    # Agrégats de base
    # -----------------------------------------------------------------------
    # Recettes réelles de fonctionnement (RRF)
    RRF = _s(s, ["70", "73", "731", "74", "75", "76", "013"])

    # Dépenses réelles de fonctionnement (DRF)
    DRF = _s(s, ["011", "012", "014", "65", "66", "67"])

    # Épargne brute
    EPARGNE_BRUTE = RRF - DRF

    # Remboursement capital
    REMB_CAPITAL = _s(s, ["16"])

    # Épargne nette
    EPARGNE_NETTE = EPARGNE_BRUTE - REMB_CAPITAL

    # Dépenses investissement — calculées depuis la situation (section I)
    df_i_dep = df_b[(df_b["Section"]=="I") & (df_b["Sens"]=="D")]
    df_i_rec = df_b[(df_b["Section"]=="I") & (df_b["Sens"]=="R")]

    def _s_i(df_sect, codes):
        total = 0.0
        for ch, data in df_sect.groupby("Chapitre"):
            code = str(ch).split("-")[0].strip()
            if code in codes:
                total += data["Réalisé"].sum()
        return total

    DEP_INV    = _s_i(df_i_dep, ["20","204","21","23","27","28"])
    DEP_EQUIP  = _s_i(df_i_dep, ["21","23"])
    SUBV_INV   = _s_i(df_i_rec, ["13"])
    FP_FLUX    = _s_i(df_i_rec, ["10","13","14"])   # flux N (recettes invest.)

    # Immobilisations brutes flux N (dépenses invest. hors 16, 040, 041)
    IMMOB_FLUX = _s_i(df_i_dep, ["20","204","21","22","23","27"])

    # Dotations amortissements flux N (68 section F)
    df_f_dep   = df_b[(df_b["Section"]=="F") & (df_b["Sens"]=="D")]
    DOT_AMORT_FLUX = _s_i(df_f_dep, ["68","681"])

    # Produit fiscal N-1 depuis Liquidé_N_1 du chapitre 73
    df_73 = df_b[df_b["Section"]=="F"]
    prod_fiscal_n1_auto = 0.0
    if "Liquidé_N_1" in df_73.columns:
        for ch, data in df_73.groupby("Chapitre"):
            code = str(ch).split("-")[0].strip()
            if code in ["73","731"]:
                prod_fiscal_n1_auto += data["Liquidé_N_1"].sum()

    # Encours dette — encours réel saisi en priorité, sinon proxy chap.16
    _encours_saisi = get_valeur(budget_label, "encours_reel") if with_saisie else 0.0
    ENCOURS_DETTE  = _encours_saisi if _encours_saisi > 0 else REMB_CAPITAL

    # Données bilan saisies
    _immob_brutes  = get_valeur(budget_label, "immob_brutes")  if with_saisie else 0.0
    _amortissements= get_valeur(budget_label, "amortissements") if with_saisie else 0.0
    _provisions    = get_valeur(budget_label, "provisions")    if with_saisie else 0.0
    _fonds_propres = get_valeur(budget_label, "fonds_propres") if with_saisie else 0.0
    _actifs_circ   = get_valeur(budget_label, "actifs_circ")   if with_saisie else 0.0
    _dettes_ct     = get_valeur(budget_label, "dettes_ct")     if with_saisie else 0.0
    _dotations_amort_saisi = get_valeur(budget_label, "dotations_amort") if with_saisie else 0.0
    _dotations_amort = _dotations_amort_saisi if _dotations_amort_saisi > 0 else DOT_AMORT_FLUX

    # Produit fiscal N-1 : saisi en priorité, sinon auto depuis Liquidé_N_1
    _prod_fiscal_n1_saisi = get_valeur(budget_label, "bases_n1_fiscal") if with_saisie else 0.0
    _prod_fiscal_n1 = _prod_fiscal_n1_saisi if _prod_fiscal_n1_saisi > 0 else prod_fiscal_n1_auto
    _immob_nettes  = _immob_brutes - _amortissements

    # Données fiscales saisies
    _bases_tf      = get_valeur(budget_label, "bases_tf")      if with_saisie else 0.0

    # Données dette saisies
    _emprunts_nv   = get_valeur(budget_label, "emprunts_nv")   if with_saisie else 0.0

    # Produit fiscal
    PROD_FISCAL = _s(s, ["73", "731"])

    # Charges personnel
    CH_PERSONNEL = _s(s, ["012"])

    # Charges générales
    CH_GENERALES = _s(s, ["011"])

    # Subventions versées
    SUBV_VERSEES = _s(s, ["65"])

    # Dotations reçues
    DOTATIONS = _s(s, ["74"])

    # Intérêts payés
    INTERETS = _s(s, ["66"])

    # Produits services
    PROD_SERVICES = _s(s, ["70"])

    # CAF = Épargne brute (simplification hors amortissements)
    CAF = EPARGNE_BRUTE

    # -----------------------------------------------------------------------
    # 1.1 Ratios d'épargne
    # -----------------------------------------------------------------------
    epargne = [
        {
            "ratio"       : "Épargne brute",
            "valeur"      : round(EPARGNE_BRUTE, 2),
            "unite"       : "€",
            "formule"     : "RRF – DRF",
            "comptes"     : "70,73,74,75,76 / 011,012,014,65,66",
            "interpretation": "Capacité structurelle à dégager du cash",
            "disponible"  : True,
        },
        {
            "ratio"       : "Épargne nette",
            "valeur"      : round(EPARGNE_NETTE, 2),
            "unite"       : "€",
            "formule"     : "Épargne brute – Remb. capital",
            "comptes"     : "16",
            "interpretation": "Capacité réelle d'autofinancement",
            "disponible"  : True,
        },
        {
            "ratio"       : "Taux d'épargne brute",
            "valeur"      : _pct(EPARGNE_BRUTE, RRF),
            "unite"       : "%",
            "formule"     : "Épargne brute / RRF × 100",
            "comptes"     : "idem",
            "interpretation": "Robustesse financière (> 15 % = sain)",
            "disponible"  : True,
        },
        {
            "ratio"       : "Taux d'épargne nette",
            "valeur"      : _pct(EPARGNE_NETTE, RRF),
            "unite"       : "%",
            "formule"     : "Épargne nette / RRF × 100",
            "comptes"     : "idem",
            "interpretation": "Soutenabilité financière (> 8 % = sain)",
            "disponible"  : True,
        },
    ]

    # -----------------------------------------------------------------------
    # 1.2 Ratios d'endettement
    # -----------------------------------------------------------------------
    endettement = [
        {
            "ratio"       : "Encours de dette / habitant",
            "valeur"      : _ratio(ENCOURS_DETTE, population),
            "unite"       : "€/hab",
            "formule"     : "Encours dette / population",
            "comptes"     : "16",
            "interpretation": "Niveau d'endettement par habitant",
            "disponible"  : True,
        },
        {
            "ratio"       : "Encours / RRF",
            "valeur"      : _pct(ENCOURS_DETTE, RRF),
            "unite"       : "%",
            "formule"     : "Encours dette / RRF × 100",
            "comptes"     : "16 / 70–76",
            "interpretation": "Poids de la dette",
            "disponible"  : True,
        },
        {
            "ratio"       : "Capacité de désendettement",
            "valeur"      : _ratio(ENCOURS_DETTE, EPARGNE_BRUTE, 1),
            "unite"       : "ans",
            "formule"     : "Encours dette / Épargne brute",
            "comptes"     : "16 / (RRF–DRF)",
            "interpretation": "< 8 ans = sain, > 12 ans = alerte",
            "disponible"  : True,
        },
        {
            "ratio"       : "Poids des intérêts",
            "valeur"      : _pct(INTERETS, DRF),
            "unite"       : "%",
            "formule"     : "Intérêts / DRF × 100",
            "comptes"     : "66 / DRF",
            "interpretation": "Charge financière annuelle",
            "disponible"  : True,
        },
    ]

    # -----------------------------------------------------------------------
    # 1.3 Ratios d'investissement
    # -----------------------------------------------------------------------
    DEP_TOTALES = DRF + DEP_INV
    investissement = [
        {
            "ratio"       : "Taux d'investissement",
            "valeur"      : _pct(DEP_INV, DEP_TOTALES),
            "unite"       : "%",
            "formule"     : "Dép. inv / Dép. totales × 100",
            "comptes"     : "20–23–27 / total",
            "interpretation": "Effort d'équipement",
            "disponible"  : True,
        },
        {
            "ratio"       : "Autofinancement investissement",
            "valeur"      : _pct(CAF, DEP_INV),
            "unite"       : "%",
            "formule"     : "CAF / Dép. inv × 100",
            "comptes"     : "CAF / 20–23–27",
            "interpretation": "Dépendance à l'emprunt",
            "disponible"  : True,
        },
        {
            "ratio"       : "Dépenses d'équipement / hab",
            "valeur"      : _ratio(DEP_EQUIP, population),
            "unite"       : "€/hab",
            "formule"     : "Dép. équipement / population",
            "comptes"     : "21–23",
            "interpretation": "Niveau d'investissement par habitant",
            "disponible"  : True,
        },
        {
            "ratio"       : "Subventions / investissement",
            "valeur"      : _pct(SUBV_INV, DEP_INV),
            "unite"       : "%",
            "formule"     : "Subv. inv / Dép. inv × 100",
            "comptes"     : "13 / 20–23–27",
            "interpretation": "Capacité à mobiliser des financements externes",
            "disponible"  : True,
        },
    ]

    # -----------------------------------------------------------------------
    # 2.1 Ratios de structure budgétaire
    # -----------------------------------------------------------------------
    structure = [
        {
            "ratio"       : "Poids des charges de personnel",
            "valeur"      : _pct(CH_PERSONNEL, DRF),
            "unite"       : "%",
            "formule"     : "012 / DRF × 100",
            "comptes"     : "012",
            "interpretation": "Rigidité structurelle (> 50 % = vigilance)",
            "disponible"  : True,
        },
        {
            "ratio"       : "Charges à caractère général",
            "valeur"      : _pct(CH_GENERALES, DRF),
            "unite"       : "%",
            "formule"     : "011 / DRF × 100",
            "comptes"     : "011",
            "interpretation": "Niveau de fonctionnement courant",
            "disponible"  : True,
        },
        {
            "ratio"       : "Subventions versées",
            "valeur"      : _pct(SUBV_VERSEES, DRF),
            "unite"       : "%",
            "formule"     : "65 / DRF × 100",
            "comptes"     : "65",
            "interpretation": "Poids des politiques publiques",
            "disponible"  : True,
        },
        {
            "ratio"       : "Part des recettes fiscales",
            "valeur"      : _pct(PROD_FISCAL, RRF),
            "unite"       : "%",
            "formule"     : "73 / RRF × 100",
            "comptes"     : "73",
            "interpretation": "Autonomie fiscale",
            "disponible"  : True,
        },
        {
            "ratio"       : "Part des dotations",
            "valeur"      : _pct(DOTATIONS, RRF),
            "unite"       : "%",
            "formule"     : "74 / RRF × 100",
            "comptes"     : "74",
            "interpretation": "Dépendance à l'État",
            "disponible"  : True,
        },
    ]

    # -----------------------------------------------------------------------
    # 2.2 Ratios de fiscalité
    # -----------------------------------------------------------------------
    fiscalite = [
        {
            "ratio"       : "Produit fiscal / habitant",
            "valeur"      : _ratio(PROD_FISCAL, population),
            "unite"       : "€/hab",
            "formule"     : "73 / population",
            "comptes"     : "731–739",
            "interpretation": "Niveau de pression fiscale",
            "disponible"  : True,
        },
        {
            "ratio"       : "Couverture des charges",
            "valeur"      : _pct(PROD_FISCAL, DRF),
            "unite"       : "%",
            "formule"     : "73 / DRF × 100",
            "comptes"     : "73 / DRF",
            "interpretation": "Autonomie financière",
            "disponible"  : True,
        },
        {
            "ratio"       : "Élasticité fiscale",
            "valeur"      : _ratio(PROD_FISCAL - _prod_fiscal_n1, _prod_fiscal_n1, 3) if _prod_fiscal_n1 > 0 else NA,
            "unite"       : "" if _prod_fiscal_n1 > 0 else "",
            "formule"     : "Variation produit fiscal / produit N-1",
            "comptes"     : "73 / bases fiscales",
            "interpretation": "Dynamisme fiscal" + ("" if _prod_fiscal_n1 > 0 else " — Produit N-1 non saisi"),
            "disponible"  : _prod_fiscal_n1 > 0,
        },
    ]

    # -----------------------------------------------------------------------
    # 2.3 Ratios patrimoniaux — données bilan non disponibles
    # -----------------------------------------------------------------------
    _bilan_ok = _immob_brutes > 0 and _amortissements > 0
    patrimoine = [
        {
            "ratio"       : "Taux de renouvellement",
            "valeur"      : _pct(_amortissements, _immob_brutes) if _bilan_ok else NA,
            "unite"       : "%" if _bilan_ok else "",
            "formule"     : "Amort. / Immob. brutes × 100",
            "comptes"     : "28 / 20–21–23",
            "interpretation": "Rythme de renouvellement" + ("" if _bilan_ok else " — Bilan requis"),
            "disponible"  : _bilan_ok,
        },
        {
            "ratio"       : "Âge moyen du patrimoine",
            "valeur"      : _ratio(_immob_nettes, _amortissements, 1) if _bilan_ok else NA,
            "unite"       : "ans" if _bilan_ok else "",
            "formule"     : "Immob. nettes / amortissements",
            "comptes"     : "20–21–23 / 28",
            "interpretation": "Vieillissement du patrimoine" + ("" if _bilan_ok else " — Bilan requis"),
            "disponible"  : _bilan_ok,
        },
        {
            "ratio"       : "Taux d'amortissement",
            "valeur"      : _pct(_dotations_amort, _immob_brutes) if (_bilan_ok and _dotations_amort > 0) else NA,
            "unite"       : "%" if (_bilan_ok and _dotations_amort > 0) else "",
            "formule"     : "Dotations / immobilisations × 100",
            "comptes"     : "681 / 20–21–23",
            "interpretation": "Politique d'amortissement" + ("" if (_bilan_ok and _dotations_amort > 0) else " — Bilan requis"),
            "disponible"  : _bilan_ok and _dotations_amort > 0,
        },
        {
            "ratio"       : "Provisions / dépenses",
            "valeur"      : _pct(_provisions, DRF) if _provisions > 0 else NA,
            "unite"       : "%" if _provisions > 0 else "",
            "formule"     : "Provisions / DRF × 100",
            "comptes"     : "15 / DRF",
            "interpretation": "Niveau de risque" + ("" if _provisions > 0 else " — Bilan requis"),
            "disponible"  : _provisions > 0,
        },
    ]

    # -----------------------------------------------------------------------
    # 3.1 Ratios de trésorerie — données bilan non disponibles
    # -----------------------------------------------------------------------
    _tres_ok = _fonds_propres > 0 and _immob_brutes > 0
    _FR      = (_fonds_propres + _provisions + ENCOURS_DETTE - _immob_nettes) if _tres_ok else 0.0
    _BFR     = (_actifs_circ - _dettes_ct) if (_actifs_circ > 0 or _dettes_ct > 0) else 0.0
    _bfr_ok  = _actifs_circ > 0 or _dettes_ct > 0
    _tres_nette_ok = _tres_ok and _bfr_ok
    tresorerie = [
        {
            "ratio"       : "Fonds de roulement",
            "valeur"      : round(_FR, 2) if _tres_ok else NA,
            "unite"       : "€" if _tres_ok else "",
            "formule"     : "(FP + Prov. + Dettes LT) – Immob. nettes",
            "comptes"     : "10–13–14–15–16 / 20–21–23",
            "interpretation": "Marge de sécurité" + ("" if _tres_ok else " — Bilan requis"),
            "disponible"  : _tres_ok,
        },
        {
            "ratio"       : "BFR",
            "valeur"      : round(_BFR, 2) if _bfr_ok else NA,
            "unite"       : "€" if _bfr_ok else "",
            "formule"     : "Actifs circulants – Dettes CT",
            "comptes"     : "41–45 / 40–42–43",
            "interpretation": "Besoin de financement" + ("" if _bfr_ok else " — Bilan requis"),
            "disponible"  : _bfr_ok,
        },
        {
            "ratio"       : "Trésorerie nette",
            "valeur"      : round(_FR - _BFR, 2) if _tres_nette_ok else NA,
            "unite"       : "€" if _tres_nette_ok else "",
            "formule"     : "FR – BFR",
            "comptes"     : "—",
            "interpretation": "Solvabilité immédiate" + ("" if _tres_nette_ok else " — Bilan requis"),
            "disponible"  : _tres_nette_ok,
        },
    ]

    # -----------------------------------------------------------------------
    # 3.2 Ratios de performance
    # -----------------------------------------------------------------------
    df_f = df_b[df_b["Section"] == "F"]
    df_i = df_b[df_b["Section"] == "I"]
    real_f  = df_f[df_f["Sens"]=="D"]["Réalisé"].sum()
    prevu_f = df_f[df_f["Sens"]=="D"]["Total_Prévu"].sum()
    real_i  = df_i[df_i["Sens"]=="D"]["Réalisé"].sum()
    prevu_i = df_i[df_i["Sens"]=="D"]["Total_Prévu"].sum()

    performance = [
        {
            "ratio"       : "Taux de réalisation F",
            "valeur"      : _pct(real_f, prevu_f),
            "unite"       : "%",
            "formule"     : "Réalisé F / Prévu F × 100",
            "comptes"     : "Tous comptes F",
            "interpretation": "Qualité de prévision budgétaire",
            "disponible"  : True,
        },
        {
            "ratio"       : "Taux de réalisation I",
            "valeur"      : _pct(real_i, prevu_i),
            "unite"       : "%",
            "formule"     : "Réalisé I / Prévu I × 100",
            "comptes"     : "Tous comptes I",
            "interpretation": "Capacité à exécuter le programme d'investissement",
            "disponible"  : True,
        },
    ]

    # -----------------------------------------------------------------------
    # 3.3 Ratios premium
    # -----------------------------------------------------------------------
    CONTINGENTS   = _s(s, ["655"])
    RIGIDITE_NUM  = CH_PERSONNEL + INTERETS + CONTINGENTS
    REC_PROPRES   = _s(s, ["73", "731", "75"])

    premium = [
        {
            "ratio"       : "Rigidité structurelle",
            "valeur"      : _pct(RIGIDITE_NUM, DRF),
            "unite"       : "%",
            "formule"     : "(012 + 661 + 655) / DRF × 100",
            "comptes"     : "012 + 66 + 655",
            "interpretation": "Marge de manœuvre (< 60 % = confortable)",
            "disponible"  : True,
        },
        {
            "ratio"       : "Effort d'investissement",
            "valeur"      : _pct(DEP_EQUIP, RRF),
            "unite"       : "%",
            "formule"     : "Dép. équipement / RRF × 100",
            "comptes"     : "21–23 / 70–76",
            "interpretation": "Ambition d'équipement",
            "disponible"  : True,
        },
        {
            "ratio"       : "Autonomie financière",
            "valeur"      : _pct(REC_PROPRES, RRF),
            "unite"       : "%",
            "formule"     : "(73 + 75) / RRF × 100",
            "comptes"     : "73 + 75 / RRF",
            "interpretation": "Dépendance externe (> 60 % = bonne autonomie)",
            "disponible"  : True,
        },
        {
            "ratio"       : "Autonomie fiscale",
            "valeur"      : _pct(PROD_FISCAL, REC_PROPRES),
            "unite"       : "%",
            "formule"     : "73 / (73 + 75) × 100",
            "comptes"     : "73 / (73+75)",
            "interpretation": "Capacité fiscale",
            "disponible"  : True,
        },
    ]

    # -----------------------------------------------------------------------
    # 4.x Ratios par habitant / ménage / emploi
    # -----------------------------------------------------------------------
    def _par(valeur, denominateur, label):
        return {
            "valeur"     : _ratio(valeur, denominateur),
            "unite"      : f"€/{label}",
            "disponible" : True,
        }

    par_habitant = [
        {"ratio": "DRF / habitant",                   **_par(DRF,           population, "hab"), "formule": "DRF / pop",         "comptes": "011–66",  "interpretation": "Niveau de service rendu"},
        {"ratio": "RRF / habitant",                   **_par(RRF,           population, "hab"), "formule": "RRF / pop",         "comptes": "70–76",   "interpretation": "Capacité financière"},
        {"ratio": "Dépenses inv. / habitant",         **_par(DEP_INV,       population, "hab"), "formule": "Inv / pop",         "comptes": "20–23–27","interpretation": "Effort d'équipement"},
        {"ratio": "Encours dette / habitant",         **_par(ENCOURS_DETTE, population, "hab"), "formule": "Encours / pop",     "comptes": "16",      "interpretation": "Niveau d'endettement"},
        {"ratio": "Intérêts payés / habitant",        **_par(INTERETS,      population, "hab"), "formule": "661 / pop",         "comptes": "66",      "interpretation": "Charge financière supportée"},
        {"ratio": "Produit fiscal / habitant",        **_par(PROD_FISCAL,   population, "hab"), "formule": "73 / pop",          "comptes": "731–739", "interpretation": "Pression fiscale réelle"},
        {"ratio": "Subventions reçues / habitant",    **_par(SUBV_INV,      population, "hab"), "formule": "13 / pop",          "comptes": "13",      "interpretation": "Attractivité des financements"},
        {"ratio": "CAF / habitant",                   **_par(CAF,           population, "hab"), "formule": "CAF / pop",         "comptes": "RRF–DRF", "interpretation": "Capacité d'autofinancement / hab"},
        {"ratio": "Dotations / habitant",             **_par(DOTATIONS,     population, "hab"), "formule": "74 / pop",          "comptes": "74",      "interpretation": "Dépendance à l'État"},
        {"ratio": "Tarification / habitant",          **_par(PROD_SERVICES, population, "hab"), "formule": "70 / pop",          "comptes": "70",      "interpretation": "Niveau de services payants"},
        {"ratio": "Charges de personnel / hab",       **_par(CH_PERSONNEL,  population, "hab"), "formule": "012 / pop",         "comptes": "012",     "interpretation": "Poids RH"},
        {"ratio": "Charges générales / hab",          **_par(CH_GENERALES,  population, "hab"), "formule": "011 / pop",         "comptes": "011",     "interpretation": "Coût des services"},
        {"ratio": "Subventions versées / hab",        **_par(SUBV_VERSEES,  population, "hab"), "formule": "65 / pop",          "comptes": "65",      "interpretation": "Effort social / associatif"},
        {"ratio": "Dépenses d'équipement / hab",      **_par(DEP_EQUIP,     population, "hab"), "formule": "21–23 / pop",       "comptes": "21–23",   "interpretation": "Niveau d'investissement"},
        {"ratio": "Subventions inv. / hab",           **_par(SUBV_INV,      population, "hab"), "formule": "13 / pop",          "comptes": "13",      "interpretation": "Capacité à mobiliser des financements"},
        {"ratio": "Emprunts nouveaux / hab",          "valeur": _ratio(_emprunts_nv, population) if _emprunts_nv > 0 else NA, "unite": "€/hab" if _emprunts_nv > 0 else "", "formule": "1641 / pop", "comptes": "1641", "interpretation": "Recours à l'endettement" + ("" if _emprunts_nv > 0 else " — Emprunts N non saisis"), "disponible": _emprunts_nv > 0},
        # Patrimoine (NA)
        {"ratio": "Valeur du patrimoine / hab",       "valeur": _ratio(_immob_nettes, population) if _bilan_ok else NA, "unite": "€/hab" if _bilan_ok else "", "formule": "Immob. nettes / pop", "comptes": "20–21–23", "interpretation": "Niveau d'équipement public" + ("" if _bilan_ok else " — Bilan requis"), "disponible": _bilan_ok},
        {"ratio": "Amortissements / hab",             "valeur": _ratio(_dotations_amort, population) if _dotations_amort > 0 else NA, "unite": "€/hab" if _dotations_amort > 0 else "", "formule": "681 / pop", "comptes": "681", "interpretation": "Coût annuel du patrimoine" + ("" if _dotations_amort > 0 else " — Bilan requis"), "disponible": _dotations_amort > 0},
    ]

    par_menage = [
        {"ratio": "DRF / ménage",                    **_par(DRF,         nb_menages, "mén"), "formule": "DRF / ménages",   "comptes": "011–66",  "interpretation": "Coût des services publics"},
        {"ratio": "Dépenses équipement / ménage",    **_par(DEP_INV,     nb_menages, "mén"), "formule": "Inv / ménages",   "comptes": "20–23",   "interpretation": "Investissement par foyer"},
        {"ratio": "Produit fiscal / ménage",         **_par(PROD_FISCAL, nb_menages, "mén"), "formule": "73 / ménages",    "comptes": "73",      "interpretation": "Pression fiscale par foyer"},
        {"ratio": "Subventions sociales / ménage",   **_par(SUBV_VERSEES,nb_menages, "mén"), "formule": "65 / ménages",    "comptes": "65",      "interpretation": "Effort social"},
    ]

    par_emploi = [
        {"ratio": "Recettes fiscales éco / emploi",  **_par(PROD_FISCAL, nb_emplois, "emp"), "formule": "73 / emplois",    "comptes": "731–739", "interpretation": "Dynamisme économique"},
        {"ratio": "Investissement éco / emploi",     **_par(DEP_INV,     nb_emplois, "emp"), "formule": "Inv / emplois",   "comptes": "20–23",   "interpretation": "Effort sur les zones d'activités"},
        {"ratio": "DRF / emploi",                    **_par(DRF,         nb_emplois, "emp"), "formule": "DRF / emplois",   "comptes": "011–66",  "interpretation": "Soutien économique"},
    ]

    return {
        "epargne"       : epargne,
        "endettement"   : endettement,
        "investissement": investissement,
        "structure"     : structure,
        "fiscalite"     : fiscalite,
        "patrimoine"    : patrimoine,
        "tresorerie"    : tresorerie,
        "performance"   : performance,
        "premium"       : premium,
        "par_habitant"  : par_habitant,
        "par_menage"    : par_menage,
        "par_emploi"    : par_emploi,
        # Agrégats utiles pour l'UI
        "_meta": {
            "RRF": RRF, "DRF": DRF,
            "EPARGNE_BRUTE": EPARGNE_BRUTE,
            "EPARGNE_NETTE": EPARGNE_NETTE,
            "DEP_INV": DEP_INV,
        },
    }


# ---------------------------------------------------------------------------
# Calcul historique — tous les ratios sur N-5 → N
# ---------------------------------------------------------------------------

ANNEES_COLS_RAT   = ["Liquidé_N_5","Liquidé_N_4","Liquidé_N_3","Liquidé_N_2","Liquidé_N_1","Réalisé"]
ANNEES_LABELS_RAT = ["N-5","N-4","N-3","N-2","N-1","N"]


def calcul_ratios_historique(
    df: pd.DataFrame,
    budget_label: str,
    population: int,
    nb_menages: int,
    nb_emplois: int,
) -> dict:
    """
    Calcule tous les ratios sur chaque année disponible (N-5 → N).

    Retourne un dict :
    {
        "labels" : ["N-5", ..., "N"],
        "ratios" : {
            "Épargne brute"      : [val_N5, ..., val_N],
            "Taux d'épargne brute": [...],
            ...
        }
    }
    """
    df_b = df[df["Libellé_budget"] == budget_label].copy()

    # Colonnes disponibles
    cols_dispo   = [c for c in ANNEES_COLS_RAT  if c in df_b.columns]
    labels_dispo = [ANNEES_LABELS_RAT[i]
                    for i, c in enumerate(ANNEES_COLS_RAT) if c in df_b.columns]

    if not cols_dispo:
        return {"labels": [], "ratios": {}}

    # Construire un df temporaire par année via remplacement de "Réalisé"
    series: dict[str, list] = {}

    for col in cols_dispo:
        # Remplacer temporairement Réalisé par la colonne historique
        df_tmp = df_b.copy()
        df_tmp["Réalisé"] = df_tmp[col]

        # Recalculer les ratios sur cette colonne
        R = calcul_ratios(df_tmp, budget_label, population, nb_menages, nb_emplois,
                          with_saisie=False)

        # Collecter tous les groupes
        tous_ratios = (
            R["epargne"] + R["endettement"] + R["investissement"] +
            R["structure"] + R["fiscalite"] + R["performance"] + R["premium"] +
            R["par_habitant"] + R["par_menage"] + R["par_emploi"]
        )

        for r in tous_ratios:
            nom = r["ratio"]
            if nom not in series:
                series[nom] = []
            series[nom].append(r["valeur"])

    return {"labels": labels_dispo, "ratios": series}
