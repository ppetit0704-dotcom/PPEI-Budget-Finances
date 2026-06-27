# ui/tab_brut.py — v2.0.0
"""Onglet 6 — Données brutes avec expanders par chapitre"""

import streamlit as st
import pandas as pd
import io
from core.utils import fmt_euros


def _to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig")


def _affiche_detail_chapitre(df: pd.DataFrame, chapitre: str):
    """Affiche le détail des comptes pour un chapitre donné."""
    df_c = df[df["Chapitre"] == chapitre].copy()
    if df_c.empty:
        st.caption("Aucune donnée.")
        return

    # Agrégation par compte + sens
    if "Compte" in df_c.columns:
        agg = (
            df_c.groupby(["Sens", "Compte"], as_index=False)
            .agg(
                Prévu    =("Total_Prévu",  "sum"),
                Réalisé  =("Réalisé",      "sum"),
                Engagé   =("Engagé",       "sum"),
            )
        )
        agg["Taux"] = agg.apply(
            lambda r: f"{r['Réalisé']/r['Prévu']*100:.1f} %" if r["Prévu"] else "—",
            axis=1,
        )
        agg["Sens"]    = agg["Sens"].map({"D": "Dépense", "R": "Recette"}).fillna(agg["Sens"])
        agg["Prévu"]   = agg["Prévu"].map(fmt_euros)
        agg["Réalisé"] = agg["Réalisé"].map(fmt_euros)
        agg["Engagé"]  = agg["Engagé"].map(fmt_euros)
        st.dataframe(agg, use_container_width=True, hide_index=True)
    else:
        # Fallback : affichage brut
        st.dataframe(df_c, use_container_width=True, hide_index=True)


def render(df_sit: pd.DataFrame, df_gl: pd.DataFrame, budget_label: str):
    st.markdown(f"### 🗄️ Données brutes — {budget_label}")

    source = st.radio("Source", ["Situation comptable", "Grand Livre"],
                       horizontal=True, key="brut_source")
    df = df_sit.copy() if source == "Situation comptable" else df_gl.copy()

    # Formatage Date GL
    if "Date" in df.columns and df["Date"].dtype != object:
        df["Date"] = df["Date"].dt.strftime("%d/%m/%Y").fillna("")

    # Filtre section + sens
    col1, col2, col3 = st.columns(3)
    with col1:
        sections = ["Toutes"] + sorted(df["Section"].dropna().unique().tolist()) if "Section" in df.columns else ["Toutes"]
        sect_sel = st.selectbox("Section", sections, key="brut_sect")
    with col2:
        sens_opts = ["Tous", "D — Dépenses", "R — Recettes"]
        sens_sel  = st.selectbox("Sens", sens_opts, key="brut_sens")
    with col3:
        search = st.text_input("🔍 Recherche globale", key="brut_search")

    if sect_sel != "Toutes" and "Section" in df.columns:
        df = df[df["Section"] == sect_sel]
    if sens_sel != "Tous" and "Sens" in df.columns:
        df = df[df["Sens"] == sens_sel.split(" — ")[0]]
    if search:
        mask = df.apply(lambda col: col.astype(str).str.contains(search, case=False, na=False))
        df   = df[mask.any(axis=1)]

    st.caption(f"{len(df):,} lignes — {len(df.columns)} colonnes")
    st.markdown("---")

    # -----------------------------------------------------------------------
    # Vue par chapitre avec expanders (Situation uniquement)
    # -----------------------------------------------------------------------
    if source == "Situation comptable" and "Chapitre" in df.columns:
        chapitres = sorted(df["Chapitre"].dropna().unique().tolist())
        st.markdown(f"**{len(chapitres)} chapitres** — cliquer pour dérouler le détail")

        for chapitre in chapitres:
            df_chap = df[df["Chapitre"] == chapitre]
            prevu   = df_chap["Total_Prévu"].sum() if "Total_Prévu" in df_chap.columns else 0
            real    = df_chap["Réalisé"].sum()     if "Réalisé"     in df_chap.columns else 0
            taux    = f"{real/prevu*100:.1f} %" if prevu else "—"

            with st.expander(
                f":violet[Détail du Chapitre {chapitre}]  —  "
                f"Prévu : {fmt_euros(prevu)}  |  Réalisé : {fmt_euros(real)}  |  Taux : {taux}",
                expanded=False,
            ):
                # Tableau de synthèse D/R
                col_d, col_r = st.columns(2)
                for col, sens_code, sens_label in [
                    (col_d, "D", "💸 Dépenses"),
                    (col_r, "R", "💰 Recettes"),
                ]:
                    with col:
                        st.caption(sens_label)
                        df_s = df_chap[df_chap["Sens"] == sens_code] if "Sens" in df_chap.columns else df_chap
                        if not df_s.empty and "Compte" in df_s.columns:
                            agg = df_s.groupby("Compte", as_index=False).agg(
                                Prévu    =("Total_Prévu","sum"),
                                Réalisé  =("Réalisé","sum"),
                                Engagé   =("Engagé","sum"),
                            )
                            agg["Taux"] = agg.apply(
                                lambda r: f"{r['Réalisé']/r['Prévu']*100:.1f} %" if r["Prévu"] else "—",
                                axis=1,
                            )
                            # Historique N-1 si disponible
                            if "Liquidé_N_1" in df_s.columns:
                                agg2 = df_s.groupby("Compte", as_index=False).agg(
                                    N_1=("Liquidé_N_1","sum"),
                                    N_2=("Liquidé_N_2","sum") if "Liquidé_N_2" in df_s.columns else ("Réalisé","sum"),
                                )
                                agg["N-1"] = agg2["N_1"].map(fmt_euros)
                                agg["N-2"] = agg2["N_2"].map(fmt_euros)
                            for c in ["Prévu","Réalisé","Engagé"]:
                                agg[c] = agg[c].map(fmt_euros)
                            st.dataframe(agg, use_container_width=True, hide_index=True)
                        else:
                            st.caption("Aucune donnée.")

    else:
        # Vue Grand Livre : tableau classique
        st.dataframe(df, use_container_width=True, hide_index=True, height=500)

    # -----------------------------------------------------------------------
    # Export
    # -----------------------------------------------------------------------
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        fname = f"ppei_budget_{source.lower().replace(' ','_')}_{budget_label.lower().replace(' ','_')}.csv"
        st.download_button("⬇️ Exporter en CSV", _to_csv(df), fname, "text/csv")
    with col2:
        try:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Export")
            st.download_button(
                "⬇️ Exporter en Excel", buf.getvalue(),
                fname.replace(".csv",".xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            st.caption("Export Excel indisponible.")
