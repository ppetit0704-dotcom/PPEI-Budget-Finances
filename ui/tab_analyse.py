# ui/tab_analyse.py
"""Onglet — Analyse résultat & Auto-financement M57"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from core.calculs import calcul_autofinancement, calcul_historique
from core.utils import fmt_euros, plotly_base_layout, COULEUR_DEP_PLOT, COULEUR_REC_PLOT

BADGE_VERT  = "#16a34a"
BADGE_ROUGE = "#dc2626"
BADGE_BLEU  = "#1d4ed8"


def _badge(label: str, valeur: float, couleur: str) -> str:
    return f"""
    <div style="background:{couleur};border-radius:8px;padding:14px 10px;
                text-align:center;color:white;min-width:140px;">
        <div style="font-size:0.78rem;font-weight:600;margin-bottom:6px;">{label}</div>
        <div style="font-size:1.05rem;font-weight:700;">{fmt_euros(valeur)}</div>
    </div>"""


def _mini_chart(labels: list, values: list, titre: str, couleur: str):
    x = labels[::-1]
    y = values[::-1]
    fig = go.Figure()
    fig.add_bar(x=x, y=y, name=titre,
                marker_color=couleur, opacity=0.35, showlegend=False)
    fig.add_scatter(
        x=x, y=y, name=titre,
        mode="lines+markers+text",
        marker=dict(size=7, color=couleur, line=dict(color="white", width=1.5)),
        line=dict(color=couleur, width=2.5),
        text=[fmt_euros(v) for v in y],
        textposition="top center",
        textfont=dict(size=8, color="#e2e8f0"),
    )
    layout = plotly_base_layout(height=240, margin=dict(t=36, b=20, l=0, r=0),
                                 title=titre)
    layout["yaxis"]["tickformat"] = ",.0f"
    fig.update_layout(**layout)
    return fig


def render(df_sit: pd.DataFrame, budget_label: str):
    st.markdown("### 💰 Analyse résultat — Auto-financement")
    if df_sit.empty:
        st.info("Aucune donnée disponible pour ce budget.")
        return

    r = calcul_autofinancement(df_sit, budget_label)
    h = calcul_historique(df_sit, budget_label)

    st.markdown(f"#### 🏅 Auto-financement ({budget_label})")
    badges = [
        ("Marge brute",           r["MARGE_BRUTE"],    BADGE_VERT),
        ("Épargne brute",         r["EPARGNE_BRUTE"],  BADGE_VERT),
        ("Dont produits except.", r["PRODUITS_AUTRES"],BADGE_ROUGE),
        ("Épargne nette",         r["EPARGNE_NETTE"],  BADGE_VERT),
        ("Report N‑1",            r["REPORT_N1"],      BADGE_BLEU),
        ("Épargne disponible",    r["DISPONIBILITE"],  BADGE_VERT),
    ]
    cols = st.columns(len(badges))
    for col, (label, valeur, couleur) in zip(cols, badges):
        with col:
            st.markdown(_badge(label, valeur, couleur), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📈 Évolution historique N‑5 → N")
    if not h["labels"]:
        st.info("Données historiques non disponibles.")
        return

    graphiques = [
        ("MARGE_BRUTE",    "Marge brute",           BADGE_VERT),
        ("EPARGNE_BRUTE",  "Épargne brute",          BADGE_VERT),
        ("PRODUITS_AUTRES","Produits exceptionnels", BADGE_ROUGE),
        ("EPARGNE_NETTE",  "Épargne nette",          BADGE_VERT),
        ("REPORT_N1",      "Report N‑1",             BADGE_BLEU),
        ("DISPONIBILITE",  "Épargne disponible",     BADGE_VERT),
    ]
    for i in range(0, len(graphiques), 2):
        col1, col2 = st.columns(2)
        for col, (cle, titre, couleur) in zip([col1, col2], graphiques[i:i+2]):
            with col:
                fig = _mini_chart(h["labels"], h[cle], titre, couleur)
                st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 Tableau récapitulatif historique"):
        rows = []
        for cle, titre, _ in graphiques:
            row = {"Indicateur": titre}
            for label, val in zip(h["labels"][::-1], h[cle][::-1]):
                row[label] = fmt_euros(val)
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander("🔍 Détail par chapitre (année N)"):
        detail = r.get("detail", {})
        if detail:
            rows_d = [{"Chapitre": k, "Réalisé": fmt_euros(v)}
                      for k, v in sorted(detail.items())]
            st.dataframe(pd.DataFrame(rows_d), use_container_width=True, hide_index=True)
