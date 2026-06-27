# ui/tab_grand_livre.py — v2.0.0
"""Onglet 5 — Grand Livre détaillé"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.utils import (
    fmt_euros, plotly_base_layout, COULEUR_DEP_PLOT, COULEUR_REC_PLOT,
)


def render(df_gl: pd.DataFrame, budget_label: str):
    st.markdown(f"### 📒 Grand Livre — {budget_label}")
    if df_gl.empty:
        st.info("Aucune donnée Grand Livre pour ce budget.")
        return

    # -----------------------------------------------------------------------
    # Filtres internes
    # -----------------------------------------------------------------------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        types_dispo = ["Tous"] + sorted(df_gl["type"].dropna().unique().tolist())
        type_sel    = st.selectbox("Type d'écriture", types_dispo)
    with col2:
        sens_dispo  = ["Tous", "D — Dépenses", "R — Recettes"]
        sens_sel    = st.selectbox("Sens", sens_dispo)
    with col3:
        # Filtre chapitre — avant le graphique mensuel
        chapitres_dispo = ["Tous"] + sorted(df_gl["Chapitre"].dropna().unique().tolist())
        chap_sel        = st.selectbox("Chapitre", chapitres_dispo)
    with col4:
        search_tiers = st.text_input("🔍 Tiers / Objet")

    df_f = df_gl.copy()
    if type_sel != "Tous":
        df_f = df_f[df_f["type"] == type_sel]
    if sens_sel != "Tous":
        df_f = df_f[df_f["Sens"] == sens_sel.split(" — ")[0]]
    if chap_sel != "Tous":
        df_f = df_f[df_f["Chapitre"] == chap_sel]
    if search_tiers:
        mask = (df_f["Tiers"].str.contains(search_tiers, case=False, na=False) |
                df_f["Objet"].str.contains(search_tiers, case=False, na=False))
        df_f = df_f[mask]

    st.caption(f"{len(df_f):,} écritures affichées sur {len(df_gl):,} total")
    st.markdown("---")

    # -----------------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------------
    liq = df_f[df_f["type"] == "Liquidation"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nb écritures",      f"{len(df_f):,}")
    c2.metric("Montant TTC total", fmt_euros(liq["Montant_TTC"].sum()))
    c3.metric("Montant HT total",  fmt_euros(liq["Montant_HT"].sum()))
    c4.metric("TVA récupérable",   fmt_euros(liq["Montant_TVA_récupérable"].sum()))
    st.markdown("---")

    # -----------------------------------------------------------------------
    # Top tiers
    # -----------------------------------------------------------------------
    st.markdown("**Top 10 tiers par montant TTC (liquidations)**")
    liq_tiers = (
        df_f[df_f["type"] == "Liquidation"]
        .groupby("Tiers", as_index=False)
        .agg(Total=("Montant_TTC","sum"), Nb=("Montant_TTC","count"))
        .sort_values("Total", ascending=False).head(10)
    )
    if not liq_tiers.empty:
        fig = go.Figure(go.Bar(
            y=liq_tiers["Tiers"], x=liq_tiers["Total"],
            orientation="h",
            marker_color=COULEUR_DEP_PLOT,
            marker_line=dict(color="#1e40af", width=0.5),
            text=[fmt_euros(v) for v in liq_tiers["Total"]],
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=9),
        ))
        layout = plotly_base_layout(height=380, margin=dict(t=20, b=20, l=0, r=90))
        layout["xaxis"]["tickformat"] = ",.0f"
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------------------------
    # Liquidations par mois (filtrées par chapitre si sélectionné)
    # -----------------------------------------------------------------------
    if "Date" in df_f.columns:
        df_dated = df_f[df_f["type"] == "Liquidation"].dropna(subset=["Date"]).copy()
        if not df_dated.empty:
            titre_mois = "**Liquidations par mois**"
            if chap_sel != "Tous":
                titre_mois += f" — {chap_sel[:50]}"
            st.markdown(titre_mois)
            df_dated["Mois"] = df_dated["Date"].dt.to_period("M").astype(str)
            par_mois = (
                df_dated.groupby("Mois", as_index=False)
                .agg(Total=("Montant_TTC","sum"), Nb=("Montant_TTC","count"))
                .sort_values("Mois")
            )
            fig2 = go.Figure(go.Bar(
                x=par_mois["Mois"], y=par_mois["Total"],
                marker_color=COULEUR_DEP_PLOT,
                text=[fmt_euros(v) for v in par_mois["Total"]],
                textposition="outside",
                textfont=dict(color="#e2e8f0", size=9),
                customdata=par_mois["Nb"],
                hovertemplate="%{x}<br>Montant TTC : %{y:,.0f} €<br>Nb écritures : %{customdata}<extra></extra>",
            ))
            layout2 = plotly_base_layout(height=300, margin=dict(t=20, b=20, l=0, r=0))
            layout2["yaxis"]["tickformat"] = ",.0f"
            fig2.update_layout(**layout2)
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Tableau détaillé
    # -----------------------------------------------------------------------
    st.markdown("**Écritures détaillées**")
    cols_affich = [
        "Date","Sens","Section","Chapitre","Imputation","type","Tiers","Objet",
        "Montant_HT","Montant_TVA_récupérable","Montant_TTC",
        "N_Pièce","N_Bordereau","Réel_Ordre",
    ]
    cols_ok  = [c for c in cols_affich if c in df_f.columns]
    df_show  = df_f[cols_ok].copy()
    for mc in ["Montant_HT","Montant_TVA_récupérable","Montant_TTC"]:
        if mc in df_show.columns:
            df_show[mc] = df_show[mc].map(fmt_euros)
    if "Date" in df_show.columns:
        df_show["Date"] = df_show["Date"].dt.strftime("%d/%m/%Y").fillna("")
    st.dataframe(df_show, use_container_width=True, hide_index=True, height=400)
