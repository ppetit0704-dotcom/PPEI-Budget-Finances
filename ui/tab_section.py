# ui/tab_section.py
"""
Onglet générique Fonctionnement (F) ou Investissement (I).
Appelé deux fois avec section_code différent.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.utils import (
    fmt_euros, fmt_pct,
    plotly_base_layout, plotly_bar_colors,
    COULEUR_PREVU, COULEUR_DEP_PLOT, COULEUR_REC_PLOT,
)


def render(df_sit: pd.DataFrame, df_gl: pd.DataFrame,
           section_code: str, section_label: str):

    st.markdown(f"### {section_label}")

    df_s = df_sit[df_sit["Section"] == section_code].copy()
    if df_s.empty:
        st.info("Aucune donnée pour cette section avec les filtres appliqués.")
        return

    # -----------------------------------------------------------------------
    # Filtre Sens interne
    # -----------------------------------------------------------------------
    sens_opts = {"Dépenses (D)": "D", "Recettes (R)": "R"}
    sens_sel  = st.radio("Afficher", list(sens_opts.keys()), horizontal=True,
                         key=f"radio_sens_{section_code}")
    sens_code = sens_opts[sens_sel]
    couleur   = COULEUR_DEP_PLOT if sens_code == "D" else COULEUR_REC_PLOT

    df_ss = df_s[df_s["Sens"] == sens_code].copy()
    if df_ss.empty:
        st.info("Pas de données pour ce sens.")
        return

    # -----------------------------------------------------------------------
    # Agrégation par chapitre
    # -----------------------------------------------------------------------
    agg = (
        df_ss.groupby("Chapitre", as_index=False)
        .agg(
            Prévu      =("Total_Prévu",  "sum"),
            Réalisé    =("Réalisé",      "sum"),
            Engagé     =("Engagé",       "sum"),
            Liquidé_N1 =("Liquidé_N_1",  "sum"),
        )
        .sort_values("Prévu", ascending=False)
    )
    agg["Taux"]      = agg.apply(lambda r: r["Réalisé"] / r["Prévu"] * 100 if r["Prévu"] else 0, axis=1)
    agg["Disponible"]= agg["Prévu"] - agg["Réalisé"]
    agg["Chap_court"]= agg["Chapitre"].str[:35]

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total prévu",   fmt_euros(agg["Prévu"].sum()))
    c2.metric("Total réalisé", fmt_euros(agg["Réalisé"].sum()))
    c3.metric("Total engagé",  fmt_euros(agg["Engagé"].sum()))
    t_global = (agg["Réalisé"].sum() / agg["Prévu"].sum() * 100) if agg["Prévu"].sum() else 0
    c4.metric("Taux global",   fmt_pct(t_global))

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Graphiques
    # -----------------------------------------------------------------------
    col_left, col_right = st.columns(2)
    h_graph = max(340, 44 * len(agg))

    # --- Graphique 1 : Prévu vs Réalisé
    with col_left:
        st.markdown("**Prévu vs Réalisé par chapitre**")
        fig = go.Figure()
        fig.add_bar(
            y=agg["Chap_court"], x=agg["Prévu"],
            name="Prévu", orientation="h",
            marker_color=COULEUR_PREVU,
            marker_line=dict(color="#60a5fa", width=0.5),
        )
        fig.add_bar(
            y=agg["Chap_court"], x=agg["Réalisé"],
            name="Réalisé", orientation="h",
            marker_color=couleur,
            marker_line=dict(color=couleur, width=0),
            text=[fmt_euros(v) for v in agg["Réalisé"]],
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=9),
        )
        layout = plotly_base_layout(height=h_graph, barmode="overlay",
                                     margin=dict(t=30, b=20, l=0, r=80))
        layout["xaxis"]["tickformat"] = ",.0f"
        layout["xaxis"]["title"] = "Montant (€)"
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    # --- Graphique 2 : Taux de réalisation
    with col_right:
        st.markdown("**Taux de réalisation par chapitre (%)**")
        agg_t = agg.sort_values("Taux", ascending=True).copy()
        couleurs_bar = plotly_bar_colors(agg_t["Taux"].tolist())

        fig2 = go.Figure(go.Bar(
            y=agg_t["Chap_court"],
            x=agg_t["Taux"].clip(upper=120),   # plafonné à 120 % visuellement
            orientation="h",
            marker_color=couleurs_bar,
            marker_line=dict(color="rgba(0,0,0,0.1)", width=0.5),
            text=[f"<b>{t:.1f}%</b>" if t >= 100 else f"{t:.1f}%"
                  for t in agg_t["Taux"]],
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=9),
            customdata=agg_t["Taux"],
            hovertemplate="%{y}<br>Taux réel : %{customdata:.1f}%<extra></extra>",
        ))
        layout2 = plotly_base_layout(height=h_graph,
                                      margin=dict(t=30, b=20, l=0, r=60))
        layout2["xaxis"]["range"]      = [0, 130]
        layout2["xaxis"]["ticksuffix"] = " %"
        layout2["xaxis"]["title"]      = "Taux de réalisation (%)"
        # Ligne de référence 100 %
        fig2.add_vline(x=100, line_dash="dash", line_color="#475569",
                       annotation_text="100 %",
                       annotation_font_color="#94a3b8",
                       annotation_font_size=9)
        fig2.update_layout(**layout2)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Tableau détaillé
    # -----------------------------------------------------------------------
    st.markdown("**Détail par chapitre**")
    display = agg[["Chapitre", "Prévu", "Réalisé", "Engagé",
                   "Disponible", "Taux", "Liquidé_N1"]].copy()
    display["Prévu"]      = display["Prévu"].map(fmt_euros)
    display["Réalisé"]    = display["Réalisé"].map(fmt_euros)
    display["Engagé"]     = display["Engagé"].map(fmt_euros)
    display["Disponible"] = display["Disponible"].map(fmt_euros)
    display["Taux"]       = display["Taux"].map(lambda x: f"{x:.1f} %")
    display["Liquidé N‑1"]= display["Liquidé_N1"].map(fmt_euros)
    display = display.drop(columns=["Liquidé_N1"])
    st.dataframe(display, use_container_width=True, hide_index=True)

    # -----------------------------------------------------------------------
    # Détail par compte
    # -----------------------------------------------------------------------
    with st.expander("🔍 Détail par compte (article budgétaire)"):
        chap_list = ["Tous"] + sorted(df_ss["Chapitre"].unique().tolist())
        chap_sel  = st.selectbox("Chapitre", chap_list,
                                  key=f"chap_{section_code}_{sens_code}")
        df_detail = df_ss if chap_sel == "Tous" else df_ss[df_ss["Chapitre"] == chap_sel]
        agg2 = (
            df_detail.groupby("Compte", as_index=False)
            .agg(Prévu=("Total_Prévu", "sum"), Réalisé=("Réalisé", "sum"),
                 Engagé=("Engagé", "sum"))
        )
        agg2["Taux"] = agg2.apply(
            lambda r: f"{r['Réalisé']/r['Prévu']*100:.1f} %" if r["Prévu"] else "—", axis=1
        )
        for c in ["Prévu", "Réalisé", "Engagé"]:
            agg2[c] = agg2[c].map(fmt_euros)
        st.dataframe(agg2, use_container_width=True, hide_index=True)
