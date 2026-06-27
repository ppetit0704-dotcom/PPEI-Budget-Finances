# ui/tab_overview.py — v2.0.0
"""Onglet 1 — Vue d'ensemble"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.utils import (
    fmt_euros, jauge_html, SENS_LABELS, SECT_LABELS,
    plotly_base_layout, COULEUR_PREVU, COULEUR_DEP_PLOT, COULEUR_REC_PLOT,
)


def render(df_sit: pd.DataFrame, df_gl: pd.DataFrame, budget_label: str):
    st.markdown(f"### 📊 Vue d'ensemble — {budget_label}")

    # -----------------------------------------------------------------------
    # Métriques globales
    # -----------------------------------------------------------------------
    total_prevu_d = df_sit[df_sit["Sens"] == "D"]["Total_Prévu"].sum()
    total_real_d  = df_sit[df_sit["Sens"] == "D"]["Réalisé"].sum()
    total_prevu_r = df_sit[df_sit["Sens"] == "R"]["Total_Prévu"].sum()
    total_real_r  = df_sit[df_sit["Sens"] == "R"]["Réalisé"].sum()
    taux_d = (total_real_d / total_prevu_d * 100) if total_prevu_d else 0
    taux_r = (total_real_r / total_prevu_r * 100) if total_prevu_r else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💸 Dépenses prévues",   fmt_euros(total_prevu_d))
    c2.metric("💸 Dépenses réalisées", fmt_euros(total_real_d), f"{taux_d:.1f} %")
    c3.metric("💰 Recettes prévues",   fmt_euros(total_prevu_r))
    c4.metric("💰 Recettes réalisées", fmt_euros(total_real_r), f"{taux_r:.1f} %")
    st.markdown("---")

    # -----------------------------------------------------------------------
    # Par section : jauges + graphique
    # -----------------------------------------------------------------------
    for sect_code, sect_label in SECT_LABELS.items():
        df_s = df_sit[df_sit["Section"] == sect_code]
        if df_s.empty:
            continue
        st.markdown(f"#### 📂 Section {sect_label}")
        col_j, col_g = st.columns([1, 2])

        with col_j:
            for sens_code, sens_label in SENS_LABELS.items():
                df_ss  = df_s[df_s["Sens"] == sens_code]
                prevu  = df_ss["Total_Prévu"].sum()
                real   = df_ss["Réalisé"].sum()
                taux   = (real / prevu * 100) if prevu else 0
                st.markdown(
                    jauge_html(f"{sens_label} ({fmt_euros(real)} / {fmt_euros(prevu)})", taux),
                    unsafe_allow_html=True,
                )

        with col_g:
            cats  = list(SENS_LABELS.values())
            prevus= [df_s[df_s["Sens"] == "D"]["Total_Prévu"].sum(),
                     df_s[df_s["Sens"] == "R"]["Total_Prévu"].sum()]
            reals = [df_s[df_s["Sens"] == "D"]["Réalisé"].sum(),
                     df_s[df_s["Sens"] == "R"]["Réalisé"].sum()]
            fig = go.Figure()
            fig.add_bar(name="Prévu",   x=cats, y=prevus,
                        marker_color=COULEUR_PREVU,
                        marker_line=dict(color="#60a5fa", width=0.5))
            fig.add_bar(name="Réalisé", x=cats, y=reals,
                        marker_color=[COULEUR_DEP_PLOT, COULEUR_REC_PLOT],
                        text=[fmt_euros(v) for v in reals],
                        textposition="outside",
                        textfont=dict(color="#e2e8f0", size=10))
            layout = plotly_base_layout(height=280, barmode="group",
                                         margin=dict(t=30, b=20, l=0, r=0))
            layout["yaxis"]["tickformat"] = ",.0f"
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

    # -----------------------------------------------------------------------
    # Tableaux récapitulatifs Dépenses ET Recettes
    # -----------------------------------------------------------------------
    col_dep, col_rec = st.columns(2)

    for col, sens_code, sens_label, couleur_titre in [
        (col_dep, "D", "Dépenses",  "#3b82f6"),
        (col_rec, "R", "Recettes",  "#22c55e"),
    ]:
        with col:
            st.markdown(
                f"<h4 style='color:{couleur_titre};'>🏛️ Récapitulatif par chapitre — {sens_label}</h4>",
                unsafe_allow_html=True,
            )
            df_s = df_sit[df_sit["Sens"] == sens_code].copy()
            if not df_s.empty:
                agg = (
                    df_s.groupby(["Section", "Chapitre"], as_index=False)
                    .agg(Prévu=("Total_Prévu","sum"),
                         Réalisé=("Réalisé","sum"),
                         Engagé=("Engagé","sum"))
                )
                agg["Section"]  = agg["Section"].map(SECT_LABELS).fillna(agg["Section"])
                agg["Taux (%)"] = agg.apply(
                    lambda r: round(r["Réalisé"] / r["Prévu"] * 100, 1) if r["Prévu"] else 0,
                    axis=1,
                )
                agg["Prévu"]    = agg["Prévu"].map(fmt_euros)
                agg["Réalisé"]  = agg["Réalisé"].map(fmt_euros)
                agg["Engagé"]   = agg["Engagé"].map(fmt_euros)
                st.dataframe(agg, use_container_width=True, hide_index=True)
