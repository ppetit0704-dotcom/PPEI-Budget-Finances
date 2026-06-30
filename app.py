# app.py — PPEI-Budget&Finances v2.0.0
"""
Application Streamlit — Analyse budgétaire et comptable M57
Situation comptable + Grand Livre
"""

import os
import sys
import streamlit as st
from threading import Timer
from pathlib import Path

# Résolution des chemins en mode PyInstaller
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

# ----------------------------------------------------------------------
# Initialisation du session_state (sécurisée)
# ----------------------------------------------------------------------
DEFAULT_SESSION = {
    "confirm_quit": False,
    "quitting": False,
}
for k, v in DEFAULT_SESSION.items():
    if k not in st.session_state:
        st.session_state[k] = v

ROOT_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Configuration page (DOIT être le 1er appel Streamlit)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PPEI — Budget & Finances",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ----------------------------------------------------------------------
# En-tête + logo
# ----------------------------------------------------------------------
col_logo, col_texte = st.columns([1, 4])
with col_logo:
    logo_path = ROOT_DIR / "assets" / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=210)

with col_texte:
    st.markdown(
        """
        <div style='margin-top:10px;'>
            <h1 class='main-title'>📊 Tableau de bord Budget/Finances (M57)</h1><br>
            <div class='sub-title'>
                Version 2.2.1 — Millésime 2026<br>
                Auteur : Philippe PETIT |
                <a href='mailto:philippe.petit.lafiou@outlook.fr?subject=Plateforme Publique [RPLS]'>Contact</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------------
# Workflow quitter
# ----------------------------------------------------------------------
if st.button("🚪 Quitter l'application", key="btn_quitter"):
    st.session_state["confirm_quit"] = True
    st.rerun()

if st.session_state["confirm_quit"]:
    st.warning("Voulez-vous vraiment quitter l'application ?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Oui, quitter maintenant"):
            st.session_state["quitting"] = True
            st.rerun()
    with col2:
        if st.button("❌ Non, annuler"):
            st.session_state["confirm_quit"] = False
            st.rerun()

if st.session_state["quitting"]:
    st.markdown("""
        <div style='text-align:center; padding-top: 80px;'>
            <h1>👋 Application fermée</h1>
            <h3 style='color:orange;'>
                Merci d'avoir utilisé le <strong>DashBoard</strong>.<br><br>
                Vous pouvez maintenant <strong>fermer cet onglet</strong>.
            </h3>
        </div>
    """, unsafe_allow_html=True)
    Timer(2, lambda: os._exit(0)).start()
    st.stop()

st.divider()

from core.utils import (
    inject_css, sidebar_filters, APP_TITLE, APP_VERSION, APP_ICON, badge_budget,
    mobile_sidebar_toggle,
)
from core.data_loader import get_situation, get_grand_livre
from core.pdf_builder import generate_pdf
import ui.tab_overview    as tab_overview
import ui.tab_section     as tab_section
import ui.tab_evolution   as tab_evolution
import ui.tab_grand_livre as tab_grand_livre
import ui.tab_brut        as tab_brut
import ui.tab_analyse     as tab_analyse
import ui.tab_ratios      as tab_ratios
import ui.tab_saisie      as tab_saisie

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
inject_css()
mobile_sidebar_toggle()

# ---------------------------------------------------------------------------
# En-tête
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="ppei-header">
        <h1>{APP_ICON} {APP_TITLE}</h1>
        <p>Analyse budgétaire et comptable — Situation M57 + Grand Livre &nbsp;|&nbsp; {APP_VERSION}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — Chargement fichiers
# ---------------------------------------------------------------------------
st.sidebar.markdown(f"## {APP_ICON} {APP_TITLE}")
st.sidebar.markdown(f"<small>{APP_VERSION}</small>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown("### 📂 Fichiers source")

path_sit = st.sidebar.text_input(
    "Situation comptable (CSV)",
    value="",
    placeholder="Chemin vers le fichier Situation…",
    key="path_sit",
)
path_gl = st.sidebar.text_input(
    "Grand Livre (CSV)",
    value="",
    placeholder="Chemin vers le fichier Grand Livre…",
    key="path_gl",
)

# Upload alternatif
with st.sidebar.expander("📤 Ou importer les fichiers"):
    up_sit = st.file_uploader("Situation (CSV)", type=["csv", "CSV"], key="up_sit")
    up_gl  = st.file_uploader("Grand Livre (CSV)", type=["csv", "CSV"], key="up_gl")

# Résolution des sources
import tempfile, shutil

def _resolve_source(path_str: str, uploaded, prefix: str):
    """Retourne un chemin fichier temporaire ou le chemin direct."""
    if uploaded is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", prefix=prefix)
        tmp.write(uploaded.getvalue())
        tmp.flush()
        tmp.close()
        return tmp.name
    if path_str and os.path.isfile(path_str):
        return path_str
    return None

src_sit = _resolve_source(path_sit, up_sit, "sit_")
src_gl  = _resolve_source(path_gl,  up_gl,  "gl_")

# ---------------------------------------------------------------------------
# Chargement des données
# ---------------------------------------------------------------------------
if src_sit is None or src_gl is None:
    st.info(
        "👈 Renseignez le chemin des fichiers CSV (ou importez-les) dans la barre latérale pour commencer."
    )
    st.markdown(
        """
        **Fichiers attendus :**
        - **Situation comptable** : export CSV situation budgétaire (séparateur `;`)
        - **Grand Livre** : export CSV Grand Livre détail par article (séparateur `;`)

        L'application détecte automatiquement l'encodage et le séparateur.
        """
    )
    st.stop()

with st.spinner("Chargement des données…"):
    try:
        df_sit = get_situation(src_sit)
        df_gl  = get_grand_livre(src_gl)
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")
        st.stop()

# ---------------------------------------------------------------------------
# Filtres sidebar → données filtrées
# ---------------------------------------------------------------------------
df_sit_f, df_gl_f, budget_sel = sidebar_filters(df_sit, df_gl)

# Badge budget dans l'en-tête
st.markdown(
    f"Analyse en cours : {badge_budget(budget_sel)}",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Export PDF
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📄 Export PDF")
    if st.button("Générer le PDF complet", use_container_width=True):
        with st.spinner("Génération du PDF…"):
            try:
                pdf_bytes = generate_pdf(df_sit_f, df_gl_f, budget_sel)
                st.download_button(
                    label="⬇️ Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"ppei_budget_{budget_sel.lower().replace(' ','_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Erreur PDF : {e}")

# ---------------------------------------------------------------------------
# Navigation par onglets
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "📊 Vue d'ensemble",
    "🏦 Fonctionnement",
    "🔨 Investissement",
    "📈 Évolution N-5",
    "📒 Grand Livre",
    "🗄️ Tableau brut",
    "💰 Analyse résultat",
    "📐 Ratios M57",
    "📝 Saisie complémentaire",
])

with tabs[0]:
    tab_overview.render(df_sit_f, df_gl_f, budget_sel)

with tabs[1]:
    tab_section.render(df_sit_f, df_gl_f, "F", "🏦 Fonctionnement")

with tabs[2]:
    tab_section.render(df_sit_f, df_gl_f, "I", "🔨 Investissement")

with tabs[3]:
    tab_evolution.render(df_sit_f, budget_sel)

with tabs[4]:
    tab_grand_livre.render(df_gl_f, budget_sel)

with tabs[5]:
    tab_brut.render(df_sit_f, df_gl_f, budget_sel)

with tabs[6]:
    # Analyse résultat : DataFrame complet (toutes sections) pour inclure chap. 16 (Investissement)
    df_sit_all_sections = df_sit[df_sit["Libellé_budget"] == budget_sel]
    tab_analyse.render(df_sit_all_sections, budget_sel)

with tabs[7]:
    # Ratios : df_sit_complet = tous budgets toutes sections (filtres indépendants)
    tab_ratios.render(df_sit_f, df_sit)

with tabs[8]:
    # Saisie complémentaire — données bilan, fiscalité, dette
    tab_saisie.render(df_sit, budget_sel)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="ppei-footer">
        PPEI — Plateforme Publique d'Échanges et d'Informations &nbsp;|&nbsp; {APP_VERSION}
        &nbsp;|&nbsp; Données : Situation M57 + Grand Livre
    </div>
    """,
    unsafe_allow_html=True,
)
