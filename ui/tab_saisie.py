# ui/tab_saisie.py
"""
@author      : Philippe PETIT
@version     : 2.0.0
@description : Onglet Saisie complémentaire
               Bilan + Fiscalité + Dette — persisté en session_state
"""

import streamlit as st
import pandas as pd
from core.saisie import (
    get_valeur, set_valeur, reset_budget, get_all,
    CHAMPS_BILAN, CHAMPS_FISCALITE, CHAMPS_DETTE,
)
from core.utils import fmt_euros, bandeau_budget_independant


# ---------------------------------------------------------------------------
# Helpers UI
# ---------------------------------------------------------------------------

def _statut_badge(budget: str, champs: list) -> str:
    """Retourne un badge HTML selon le taux de remplissage."""
    remplis = sum(1 for c, *_ in champs if get_valeur(budget, c) > 0)
    total   = len(champs)
    pct     = remplis / total * 100 if total else 0
    if pct == 100:
        coul, label = "#16a34a", f"✅ Complet ({remplis}/{total})"
    elif pct > 0:
        coul, label = "#f59e0b", f"⚠️ Partiel ({remplis}/{total})"
    else:
        coul, label = "#dc2626", f"❌ Non renseigné (0/{total})"
    return (
        f"<span style='background:{coul};color:white;border-radius:12px;"
        f"padding:3px 12px;font-size:0.78rem;font-weight:600;'>{label}</span>"
    )


def _groupe_saisie(budget: str, champs: list, prefixe_key: str):
    """Affiche un groupe de champs de saisie avec sauvegarde immédiate."""
    cols_header = st.columns([3, 2, 1, 1])
    cols_header[0].markdown("**Libellé**")
    cols_header[1].markdown("**Comptes M57**")
    cols_header[2].markdown("**Valeur (€)**")
    cols_header[3].markdown("**Statut**")

    for cle, libelle, aide, compte in champs:
        valeur_actuelle = get_valeur(budget, cle)
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

        with col1:
            st.markdown(f"<small><b>{libelle}</b><br>"
                        f"<span style='color:#94a3b8;font-size:0.72rem;'>{aide}</span></small>",
                        unsafe_allow_html=True)
        with col2:
            st.markdown(f"<small style='color:#60a5fa;font-family:monospace;'>{compte}</small>",
                        unsafe_allow_html=True)
        with col3:
            nouvelle_val = st.number_input(
                label=libelle,
                value=float(valeur_actuelle),
                min_value=0.0,
                step=1000.0,
                format="%.2f",
                label_visibility="collapsed",
                key=f"{prefixe_key}_{budget}_{cle}",
            )
            if nouvelle_val != valeur_actuelle:
                set_valeur(budget, cle, nouvelle_val)
        with col4:
            if nouvelle_val > 0:
                st.markdown("🟢", unsafe_allow_html=True)
            else:
                st.markdown("⚪", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render(df_sit: pd.DataFrame, budget_label: str):
    st.markdown("### 📝 Saisie complémentaire")

    # Bandeau budget indépendant
    _budget_courant_saisie = st.session_state.get("saisie_budget_sel", "")
    bandeau_budget_independant(_budget_courant_saisie)

    st.caption(
        "Ces données complètent les exports CSV pour débloquer les ratios patrimoniaux, "
        "de trésorerie et fiscaux. Elles sont conservées pendant toute la session."
    )

    # Sélection budget (peut différer du filtre sidebar)
    budgets_dispo = sorted(df_sit["Libellé_budget"].dropna().unique().tolist())
    budget = st.selectbox(
        "Budget à renseigner",
        budgets_dispo,
        index=budgets_dispo.index(budget_label) if budget_label in budgets_dispo else 0,
        key="saisie_budget_sel",
    )

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Indicateur global de complétude
    # -----------------------------------------------------------------------
    tous_champs = CHAMPS_BILAN + CHAMPS_FISCALITE + CHAMPS_DETTE
    remplis_total = sum(1 for c, *_ in tous_champs if get_valeur(budget, c) > 0)
    pct_global    = remplis_total / len(tous_champs) * 100

    col_stat, col_reset = st.columns([4, 1])
    with col_stat:
        st.markdown(
            f"**Complétude globale — {budget}** &nbsp;&nbsp;"
            f"{_statut_badge(budget, tous_champs)} &nbsp;&nbsp;"
            f"<small style='color:#94a3b8;'>{remplis_total}/{len(tous_champs)} champs renseignés</small>",
            unsafe_allow_html=True,
        )
        # Barre de progression
        st.progress(int(pct_global))

    with col_reset:
        if st.button("🔄 Réinitialiser", key=f"reset_{budget}",
                     help="Remet à zéro tous les champs de ce budget"):
            reset_budget(budget)
            st.rerun()

    st.markdown("---")

    # -----------------------------------------------------------------------
    # 3 sous-tabs de saisie
    # -----------------------------------------------------------------------
    t_bilan, t_fiscal, t_dette = st.tabs([
        "🏛️ Bilan comptable",
        "🧮 Fiscalité",
        "💳 Dette",
    ])

    with t_bilan:
        st.markdown("#### Données de bilan")
        st.caption("Source : compte de gestion / bilan comptable M57 au 31/12 de l'exercice.")
        st.markdown(
            _statut_badge(budget, CHAMPS_BILAN),
            unsafe_allow_html=True,
        )
        st.markdown("")
        _groupe_saisie(budget, CHAMPS_BILAN, "bilan")

        # Calculs dérivés automatiques


        st.markdown("---")
        st.info(
            "💡 Les **immobilisations flux N** (20+21+23+204), **subventions reçues** (13) "
            "et **dotations aux amortissements** (68) sont automatiquement extraites "
            "de la situation comptable. Seules les données de **stock bilan** (cumulées au 31/12) "
            "nécessitent une saisie manuelle ci-dessus."
        )
        amort  = get_valeur(budget, "amortissements")
        prov   = get_valeur(budget, "provisions")
        fp     = get_valeur(budget, "fonds_propres")
        ac     = get_valeur(budget, "actifs_circ")
        dct    = get_valeur(budget, "dettes_ct")
        enc    = get_valeur(budget, "encours_reel")

        if amort > 0 or fp > 0:
            st.markdown("**🔢 Calculs dérivés (nécessitent bilan saisi)**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Amortissements cumulés", fmt_euros(amort),
                      help="Saisi manuellement — stock bilan")
            c2.metric("Fonds propres cumulés",  fmt_euros(fp),
                      help="Saisi manuellement — stock bilan")
            c3.metric("Provisions",             fmt_euros(prov),
                      help="Saisi manuellement — stock bilan")
            if ac > 0 or dct > 0:
                bfr = ac - dct
                st.metric("BFR estimé", fmt_euros(bfr),
                          help="Actifs circulants − Dettes CT")

    with t_fiscal:
        st.markdown("#### Données fiscales")
        st.caption("Source : états fiscaux, notification des bases d'imposition (DGFIP).")
        st.markdown(
            _statut_badge(budget, CHAMPS_FISCALITE),
            unsafe_allow_html=True,
        )
        st.markdown("")
        _groupe_saisie(budget, CHAMPS_FISCALITE, "fiscal")

        st.markdown("---")
        st.info(
            "💡 Le **produit fiscal N-1** est automatiquement extrait de la colonne "
            "`Liquidé_N_1` des chapitres 73 et 731 de la situation comptable. "
            "Le champ 'override' ci-dessus ne sert qu'à corriger cette valeur si nécessaire."
        )
        bases_tf = get_valeur(budget, "bases_tf")
        prod_n   = get_valeur(budget, "bases_n1_fiscal")
        if bases_tf > 0 or prod_n > 0:
            st.markdown("**🔢 Aperçu fiscal**")
            c1, c2 = st.columns(2)
            c1.metric("Bases TF bâti saisies",  fmt_euros(bases_tf))
            c2.metric("Produit N-1 (override)", fmt_euros(prod_n),
                      help="0 = valeur auto depuis Liquidé_N_1")

    with t_dette:
        st.markdown("#### Données de dette")
        st.caption("Source : état de la dette, tableau d'amortissement des emprunts.")
        st.markdown(
            _statut_badge(budget, CHAMPS_DETTE),
            unsafe_allow_html=True,
        )
        st.markdown("")
        _groupe_saisie(budget, CHAMPS_DETTE, "dette")

        # Récap dette auto
        encours  = get_valeur(budget, "encours_reel")
        emp_nv   = get_valeur(budget, "emprunts_nv")
        annuite  = get_valeur(budget, "annuite_totale")
        if encours > 0:
            st.markdown("---")
            st.markdown("**🔢 Récapitulatif dette**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Encours réel",      fmt_euros(encours))
            c2.metric("Emprunts nouveaux", fmt_euros(emp_nv))
            c3.metric("Annuité totale",    fmt_euros(annuite))

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Récapitulatif exportable
    # -----------------------------------------------------------------------
    with st.expander("📋 Récapitulatif des données saisies"):
        all_vals = get_all(budget)
        if all_vals:
            rows = []
            champ_map = {c: (l, cp) for c, l, _, cp in tous_champs}
            for cle, val in all_vals.items():
                if val > 0 and cle in champ_map:
                    libelle, compte = champ_map[cle]
                    rows.append({
                        "Champ"      : libelle,
                        "Compte M57" : compte,
                        "Valeur"     : fmt_euros(val),
                    })
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info("Aucune donnée saisie pour ce budget.")
        else:
            st.info("Aucune donnée saisie pour ce budget.")

    # -----------------------------------------------------------------------
    # Info ratios débloqués
    # -----------------------------------------------------------------------
    st.markdown("#### 🔓 Ratios débloqués par vos saisies")
    debloques = []
    bloques   = []

    checks = [
        (["amortissements"], "Taux de renouvellement, âge moyen du patrimoine (2.3) — amortissements cumulés bilan"),
        (["fonds_propres","actifs_circ","dettes_ct"], "Fonds de roulement, BFR, trésorerie nette (3.1)"),
        (["encours_reel"], "Capacité de désendettement affinée, encours réel / habitant (1.2)"),
        (["bases_tf"], "Élasticité fiscale (2.2) — bases fiscales + produit N-1 auto depuis situation"),
        (["emprunts_nv"], "Emprunts nouveaux / habitant (4.5)"),
    ]
    # Toujours disponibles grâce à la situation
    debloques.insert(0, "✅ Dépenses d'investissement (20+21+23+204) — extrait automatiquement")
    debloques.insert(1, "✅ Dotations amortissements flux N (68) — extrait automatiquement")
    debloques.insert(2, "✅ Produit fiscal N-1 (Liquidé_N_1 chap.73) — extrait automatiquement")
    for champs_requis, label in checks:
        if all(get_valeur(budget, c) > 0 for c in champs_requis):
            debloques.append(f"✅ {label}")
        else:
            manquants = [c for c in champs_requis if get_valeur(budget, c) == 0]
            bloques.append(f"🔒 {label} — manque : {', '.join(manquants)}")

    if debloques:
        for d in debloques:
            st.success(d)
    if bloques:
        for b in bloques:
            st.warning(b)
    if not debloques and not bloques:
        st.info("Renseignez les données ci-dessus pour débloquer les ratios avancés.")
