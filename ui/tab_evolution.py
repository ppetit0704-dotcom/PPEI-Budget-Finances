# ui/tab_evolution.py — v2.0.0
"""Onglet 4 — Évolution historique N-5 à N"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.utils import (
    fmt_euros, SECT_LABELS,
    plotly_base_layout, COULEUR_DEP_PLOT, COULEUR_REC_PLOT,
)

# N-5 → N-1 depuis les colonnes historiques + N depuis "Réalisé"
ANNEES_COLS  = ["Liquidé_N_5","Liquidé_N_4","Liquidé_N_3","Liquidé_N_2","Liquidé_N_1","Réalisé"]
ANNEES_LABEL = ["N-5","N-4","N-3","N-2","N-1","N"]


def render(df_sit: pd.DataFrame, budget_label: str):
    st.markdown(f"### 📈 Évolution historique — {budget_label}")
    st.caption("Liquidations N‑5 à N (exercice courant) par section et sens.")

    # Colonnes réellement disponibles
    cols_dispo   = [c for c in ANNEES_COLS  if c in df_sit.columns]
    labels_dispo = [ANNEES_LABEL[i] for i, c in enumerate(ANNEES_COLS) if c in df_sit.columns]

    if not cols_dispo:
        st.warning("Aucune colonne historique disponible.")
        return

    for sect_code, sect_label in SECT_LABELS.items():
        df_s = df_sit[df_sit["Section"] == sect_code]
        if df_s.empty:
            continue
        st.markdown(f"#### 📂 {sect_label}")
        fig = go.Figure()
        for sens_code, sens_label, couleur in [
            ("D", "Dépenses", COULEUR_DEP_PLOT),
            ("R", "Recettes", COULEUR_REC_PLOT),
        ]:
            df_ss   = df_s[df_s["Sens"] == sens_code]
            valeurs = [df_ss[c].sum() for c in cols_dispo]
            # Affichage N-5 → N (déjà dans l'ordre)
            fig.add_bar(
                x=labels_dispo, y=valeurs,
                name=f"{sens_label} (barres)",
                marker_color=couleur, opacity=0.35,
                showlegend=False,
            )
            fig.add_scatter(
                x=labels_dispo, y=valeurs, name=sens_label,
                mode="lines+markers+text",
                marker=dict(size=8, color=couleur,
                            line=dict(color="white", width=1.5)),
                line=dict(color=couleur, width=2.5),
                text=[fmt_euros(v) for v in valeurs],
                textposition="top center",
                textfont=dict(size=9, color="#e2e8f0"),
            )
        layout = plotly_base_layout(height=320, margin=dict(t=40, b=20, l=0, r=0))
        layout["yaxis"]["tickformat"] = ",.0f"
        layout["hovermode"] = "x unified"
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

        with st.expander(f"Tableau — {sect_label}"):
            rows = []
            for sens_code, sens_label in [("D","Dépenses"),("R","Recettes")]:
                df_ss = df_s[df_s["Sens"] == sens_code]
                row   = {"Sens": sens_label}
                for col, lbl in zip(cols_dispo, labels_dispo):
                    row[lbl] = fmt_euros(df_ss[col].sum())
                rows.append(row)
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # -----------------------------------------------------------------------
    # Zoom chapitre — axe N-5 → N
    # -----------------------------------------------------------------------
    st.markdown("---")
    st.markdown("#### 🔍 Zoom chapitre")
    chapitres = sorted(df_sit["Chapitre"].dropna().unique().tolist())
    chap_sel  = st.selectbox("Chapitre", chapitres)
    sens_sel  = st.radio("Sens", ["Dépenses (D)", "Recettes (R)"],
                          horizontal=True, key="evol_sens")
    sens_code = "D" if "D" in sens_sel else "R"
    couleur   = COULEUR_DEP_PLOT if sens_code == "D" else COULEUR_REC_PLOT

    df_c = df_sit[(df_sit["Chapitre"] == chap_sel) & (df_sit["Sens"] == sens_code)]
    if df_c.empty:
        st.info("Pas de données.")
        return

    valeurs = [df_c[c].sum() for c in cols_dispo]   # déjà N-5 → N

    fig2 = go.Figure(go.Bar(
        x=labels_dispo, y=valeurs,
        marker_color=couleur,
        text=[fmt_euros(v) for v in valeurs],
        textposition="outside",
        textfont=dict(color="#e2e8f0", size=9),
    ))
    layout2 = plotly_base_layout(height=300, margin=dict(t=20, b=20, l=0, r=0))
    layout2["yaxis"]["tickformat"] = ",.0f"
    fig2.update_layout(**layout2)
    st.plotly_chart(fig2, use_container_width=True)
