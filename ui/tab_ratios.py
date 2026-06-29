# ui/tab_ratios.py — v2.1.0
"""
Onglet — Ratios M57
4 sous-tabs :
  1. Épargne + Endettement
  2. Investissement + Structure budgétaire
  3. Fiscalité + Patrimoine + Trésorerie + Performance + Premium
  4. Par habitant + Par ménage + Par emploi
Chaque ratio dispose d'un expander 📈 Évolution N‑5 → N.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.ratios import calcul_ratios, calcul_ratios_historique
from core.utils import fmt_euros, fmt_pct, plotly_base_layout, bandeau_budget_independant

# Valeurs par défaut INSEE
DEFAULT_POPULATION = 2243
DEFAULT_MENAGES    = 875
DEFAULT_EMPLOIS    = 1147

NA_MSG = "⚠️ Données non disponibles"


# ---------------------------------------------------------------------------
# Helpers UI — formatage valeur ratio
# ---------------------------------------------------------------------------

def _fmt_val_ratio(val, unite: str) -> str:
    if val is None:
        return "—"
    elif unite == "%":
        return fmt_pct(val)
    elif unite == "€":
        return fmt_euros(val)
    elif unite.startswith("€/"):
        return f"{val:,.2f} {unite}".replace(",", "\u202f")
    elif unite == "ans":
        return f"{val:.1f} ans"
    else:
        return f"{val}"


def _couleur_ratio(valeur, seuils: tuple = None) -> str:
    if valeur is None:
        return "#94a3b8"
    if seuils:
        bas, haut = seuils
        if valeur < bas:
            return "#22c55e"
        elif valeur > haut:
            return "#ef4444"
    return "#3b82f6"


# ---------------------------------------------------------------------------
# Carte ratio
# ---------------------------------------------------------------------------

def _carte_ratio(ratio: dict, seuils: tuple = None):
    if not ratio["disponible"]:
        st.markdown(
            f"""<div style="background:#1e293b;border-radius:8px;padding:12px;
                border-left:4px solid #475569;margin-bottom:6px;">
                <div style="font-size:0.78rem;color:#94a3b8;font-weight:600;">{ratio['ratio']}</div>
                <div style="font-size:0.82rem;color:#64748b;margin-top:4px;">{NA_MSG}</div>
                <div style="font-size:0.70rem;color:#475569;margin-top:2px;font-style:italic;">{ratio['formule']}</div>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    val   = ratio["valeur"]
    unite = ratio["unite"]
    coul  = _couleur_ratio(val, seuils)
    val_str = _fmt_val_ratio(val, unite)

    st.markdown(
        f"""<div style="background:#1e293b;border-radius:8px;padding:12px;
            border-left:4px solid {coul};box-shadow:0 1px 3px rgba(0,0,0,0.3);margin-bottom:6px;">
            <div style="font-size:0.78rem;color:#94a3b8;font-weight:600;">{ratio['ratio']}</div>
            <div style="font-size:1.1rem;color:{coul};font-weight:700;margin-top:4px;">{val_str}</div>
            <div style="font-size:0.70rem;color:#64748b;margin-top:3px;">
                {ratio['interpretation']}<br>
                <span style="font-style:italic;">{ratio['formule']}</span>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Tableau synthétique
# ---------------------------------------------------------------------------

def _tableau_ratios(ratios: list, title: str):
    rows = []
    for r in ratios:
        rows.append({
            "Ratio"         : r["ratio"],
            "Valeur"        : _fmt_val_ratio(r["valeur"], r["unite"]),
            "Formule"       : r["formule"],
            "Comptes M57"   : r["comptes"],
            "Interprétation": r["interpretation"],
        })
    st.caption(title)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Expander évolution historique N-5 → N
# ---------------------------------------------------------------------------

def _expander_evolution(ratio: dict, H: dict, groupe: str, idx: int):
    """
    Expander avec courbe d'évolution N-5 → N pour un ratio.
    groupe + idx garantissent une clé unique même si le même ratio
    apparaît dans plusieurs groupes (ex: Produit fiscal / habitant).
    """
    nom    = ratio["ratio"]
    unite  = ratio["unite"]
    labels = H.get("labels", [])
    valeurs = H.get("ratios", {}).get(nom, [])

    # Filtrer les None
    points = [(l, v) for l, v in zip(labels, valeurs) if v is not None]

    # Clé unique : groupe + index dans le groupe
    safe_nom  = "".join(c if c.isalnum() else "_" for c in nom)
    chart_key = f"evol_{groupe}_{idx}_{safe_nom}"

    with st.expander(f"📈 {nom} — Évolution N‑5 → N", expanded=False):
        if len(points) < 2:
            st.caption("Données historiques insuffisantes pour ce ratio.")
            return

        x_vals = [p[0] for p in points]
        y_vals = [p[1] for p in points]

        def _fmt(v):
            return _fmt_val_ratio(v, unite)

        delta   = y_vals[-1] - y_vals[0]
        couleur = "#22c55e" if delta >= 0 else "#ef4444"
        fill_c  = "rgba(34,197,94,0.10)" if delta >= 0 else "rgba(239,68,68,0.10)"

        fig = go.Figure()
        # Zone de remplissage
        fig.add_scatter(
            x=x_vals, y=y_vals,
            mode="none", fill="tozeroy",
            fillcolor=fill_c,
            showlegend=False, hoverinfo="skip",
        )
        # Courbe + points + valeurs annotées
        fig.add_scatter(
            x=x_vals, y=y_vals,
            mode="lines+markers+text",
            line=dict(color=couleur, width=2.5),
            marker=dict(size=8, color=couleur,
                        line=dict(color="white", width=1.5)),
            text=[_fmt(v) for v in y_vals],
            textposition="top center",
            textfont=dict(size=9, color="#e2e8f0"),
            hovertemplate="%{x} : %{text}<extra></extra>",
            showlegend=False,
        )

        layout = plotly_base_layout(height=200, margin=dict(t=30, b=10, l=0, r=0))
        layout["yaxis"]["tickformat"] = ",.1f"
        layout["xaxis"]["showgrid"]   = False
        fig.update_layout(**layout)

        delta_txt = (f"+{_fmt(abs(delta))}" if delta >= 0 else f"-{_fmt(abs(delta))}")
        delta_col = "#22c55e" if delta >= 0 else "#ef4444"

        col_fig, col_stat = st.columns([4, 1])
        with col_fig:
            st.plotly_chart(fig, use_container_width=True, key=chart_key)
        with col_stat:
            st.markdown(
                f"""<div style='text-align:center;padding-top:36px;'>
                    <div style='font-size:0.70rem;color:#94a3b8;'>Δ N‑5 → N</div>
                    <div style='font-size:0.95rem;font-weight:700;color:{delta_col};'>{delta_txt}</div>
                    <div style='font-size:0.68rem;color:#64748b;margin-top:6px;line-height:1.6;'>
                        Min : {_fmt(min(y_vals))}<br>Max : {_fmt(max(y_vals))}
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Grille de cartes + expanders
# ---------------------------------------------------------------------------

def _grille(ratios: list, groupe: str, nb_cols: int = 3,
            seuils_map: dict = None, H: dict = None):
    """
    Affiche les ratios en grille (nb_cols colonnes) puis
    un expander évolution sous chaque carte.
    groupe : identifiant textuel unique du groupe (ex: "epargne", "par_habitant")
    """
    seuils_map = seuils_map or {}
    H          = H or {"labels": [], "ratios": {}}

    # Grille de cartes
    cols = st.columns(nb_cols)
    for i, r in enumerate(ratios):
        with cols[i % nb_cols]:
            _carte_ratio(r, seuils_map.get(r["ratio"]))

    # Expanders évolution — pleine largeur, un par ratio
    for i, r in enumerate(ratios):
        _expander_evolution(r, H, groupe=groupe, idx=i)


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render(df_sit: pd.DataFrame, df_sit_complet: pd.DataFrame):
    st.markdown("### 📐 Ratios M57")

    # Bandeau budget indépendant
    _budgets_courants = st.session_state.get("ratio_budgets", [])
    _budget_affiche_courant = _budgets_courants[0] if _budgets_courants else ""
    bandeau_budget_independant(_budget_affiche_courant)

    # -----------------------------------------------------------------------
    # Paramètres démographiques + sélection budgets
    # -----------------------------------------------------------------------
    with st.expander("⚙️ Paramètres de calcul", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            population = st.number_input(
                "Population (INSEE)", min_value=1,
                value=DEFAULT_POPULATION, step=1,
                help="RP2022 — géographie au 01/01/2025",
                key="ratio_pop",
            )
        with col2:
            nb_menages = st.number_input(
                "Nb ménages (INSEE)", min_value=1,
                value=DEFAULT_MENAGES, step=1,
                help="RP2022 exploitations complémentaires",
                key="ratio_men",
            )
        with col3:
            nb_emplois = st.number_input(
                "Nb emplois actifs (INSEE)", min_value=1,
                value=DEFAULT_EMPLOIS, step=1,
                help="RP2022 — lieu résidence + travail",
                key="ratio_emp",
            )
        st.caption(
            "Sources : INSEE, RP2011, RP2016 et RP2022, exploitations principales, "
            "géographie au 01/01/2025."
        )
        budgets_dispo = sorted(df_sit_complet["Libellé_budget"].dropna().unique().tolist())
        budgets_sel   = st.multiselect(
            "Budgets à inclure dans les ratios",
            budgets_dispo, default=budgets_dispo[:1],
            key="ratio_budgets",
        )

    if not budgets_sel:
        st.info("Sélectionnez au moins un budget.")
        return

    # Calcul ratios N
    resultats = {}
    for b in budgets_sel:
        resultats[b] = calcul_ratios(
            df_sit_complet, b,
            int(population), int(nb_menages), int(nb_emplois),
        )

    budget_affiche = budgets_sel[0] if len(budgets_sel) == 1 else st.selectbox(
        "Afficher les ratios du budget :", budgets_sel, key="ratio_budget_aff",
    )

    R = resultats[budget_affiche]

    # Calcul historique N-5 → N (une seule fois pour tous les ratios)
    with st.spinner("Calcul de l'évolution historique…"):
        H = calcul_ratios_historique(
            df_sit_complet, budget_affiche,
            int(population), int(nb_menages), int(nb_emplois),
        )

    st.markdown(f"**Budget : {budget_affiche}** — {len(H['labels'])} exercices disponibles")
    st.markdown("---")

    # -----------------------------------------------------------------------
    # 4 sous-tabs
    # -----------------------------------------------------------------------
    t1, t2, t3, t4 = st.tabs([
        "🧱 Épargne & Endettement",
        "🏗️ Investissement & Structure",
        "🧾 Fiscalité & Patrimoine & Performance",
        "🧍 Par habitant, ménage & emploi",
    ])

    # ===== TAB 1 =====
    with t1:
        st.markdown("#### 1.1 — Ratios d'épargne")
        _grille(R["epargne"], groupe="epargne", nb_cols=2, H=H, seuils_map={
            "Taux d'épargne brute": (15, 30),
            "Taux d'épargne nette": (8, 20),
        })
        st.markdown("---")
        st.markdown("#### 1.2 — Ratios d'endettement")
        _grille(R["endettement"], groupe="endettement", nb_cols=2, H=H, seuils_map={
            "Capacité de désendettement": (0, 8),
            "Poids des intérêts"        : (0, 5),
        })
        with st.expander("📋 Tableau synthétique"):
            _tableau_ratios(R["epargne"] + R["endettement"], "Épargne & Endettement")

    # ===== TAB 2 =====
    with t2:
        st.markdown("#### 1.3 — Ratios d'investissement")
        _grille(R["investissement"], groupe="investissement", nb_cols=2, H=H)
        st.markdown("---")
        st.markdown("#### 2.1 — Structure budgétaire")
        _grille(R["structure"], groupe="structure", nb_cols=3, H=H, seuils_map={
            "Poids des charges de personnel": (40, 55),
        })
        st.markdown("---")
        st.markdown("#### 3.2 — Performance budgétaire")
        _grille(R["performance"], groupe="performance", nb_cols=2, H=H)
        st.markdown("---")
        st.markdown("#### 3.3 — Ratios premium")
        _grille(R["premium"], groupe="premium", nb_cols=2, H=H, seuils_map={
            "Rigidité structurelle": (50, 65),
            "Autonomie financière" : (40, 60),
        })
        with st.expander("📋 Tableau synthétique"):
            _tableau_ratios(
                R["investissement"] + R["structure"] + R["performance"] + R["premium"],
                "Investissement & Structure",
            )

    # ===== TAB 3 =====
    with t3:
        st.markdown("#### 2.2 — Ratios de fiscalité")
        _grille(R["fiscalite"], groupe="fiscalite", nb_cols=3, H=H)
        st.markdown("---")
        st.markdown("#### 2.3 — Ratios patrimoniaux")
        _grille(R["patrimoine"], groupe="patrimoine", nb_cols=2, H=H)
        st.markdown("---")
        st.markdown("#### 3.1 — Ratios de trésorerie")
        _grille(R["tresorerie"], groupe="tresorerie", nb_cols=3, H=H)
        with st.expander("📋 Tableau synthétique"):
            _tableau_ratios(
                R["fiscalite"] + R["patrimoine"] + R["tresorerie"],
                "Fiscalité & Patrimoine & Trésorerie",
            )

    # ===== TAB 4 =====
    with t4:
        st.markdown("#### 4.x — Ratios par habitant")
        _grille(R["par_habitant"], groupe="par_habitant", nb_cols=3, H=H)
        st.markdown("---")
        st.markdown("#### 4.6 — Ratios par ménage")
        _grille(R["par_menage"], groupe="par_menage", nb_cols=2, H=H)
        st.markdown("---")
        st.markdown("#### 4.7 — Ratios par emploi")
        _grille(R["par_emploi"], groupe="par_emploi", nb_cols=3, H=H)
        with st.expander("📋 Tableau synthétique"):
            _tableau_ratios(
                R["par_habitant"] + R["par_menage"] + R["par_emploi"],
                "Par habitant, ménage & emploi",
            )
