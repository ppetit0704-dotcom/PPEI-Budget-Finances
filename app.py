# ======================================================================
# APPLICATION RPLS — VERSION ULTRA‑PRO FULL COMBO (Monofichier)
# Auteur : Philippe PETIT
# Architecture : Premium, robuste, performante, UI haut de gamme
# ======================================================================

import streamlit as st
import pandas as pd
import numpy as np
import time
import sys
import os
import logging
from pathlib import Path
from threading import Timer
from functools import lru_cache

import plotly.express as px
import plotly.graph_objects as go

import requests
from functools import lru_cache

# ======================================================================
# IMPORTS POUR LE PDF (à ajouter en haut du fichier)
# ======================================================================
from io import BytesIO
import tempfile
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
import plotly.io as pio


# ======================================================================
# CLASSE PDFBUILDER — RAPPORT PREMIUM
# ======================================================================
class PDFBuilder:
    def __init__(self, df, territoire_label, dep_code, logo_path=None):
        self.df = df
        self.territoire_label = territoire_label
        self.dep_code = dep_code
        self.logo_path = logo_path
        self.buffer = BytesIO()

        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name="TitreSection",
            fontSize=16,
            leading=20,
            spaceAfter=12,
            textColor=colors.HexColor("#1a3a5c"),
            fontName="Helvetica-Bold"
        ))
        self.styles.add(ParagraphStyle(
            name="SousTitre",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#5a7a9c"),
        ))
        self.styles.add(ParagraphStyle(
            name="Texte",
            fontSize=9,
            leading=12,
        ))
        self.styles.add(ParagraphStyle(
            name="Chip",
            fontSize=9,
            leading=11,
            textColor=colors.white,
        ))

    # --------------------------------------------------------------
    # HEADER / FOOTER
    # --------------------------------------------------------------
    def _header_footer(self, canvas, doc):
        canvas.saveState()

        # En-tête
        if self.logo_path and os.path.exists(self.logo_path):
            canvas.drawImage(
                str(self.logo_path),
                x=1.5*cm, y=A4[1] - 2.2*cm,
                width=1.6*cm, height=1.6*cm,
                preserveAspectRatio=True, mask='auto'
            )

        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(colors.HexColor("#1a3a5c"))
        canvas.drawString(3.5*cm, A4[1] - 1.5*cm, "RPLS – Analyse territoriale des logements sociaux")

        canvas.setStrokeColor(colors.HexColor("#d0dcea"))
        canvas.setLineWidth(0.5)
        canvas.line(1.5*cm, A4[1] - 1.8*cm, A4[0] - 1.5*cm, A4[1] - 1.8*cm)

        # Pied de page
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(1.5*cm, 1.5*cm, f"Territoire : {self.territoire_label} — Département {self.dep_code}")
        canvas.drawRightString(A4[0] - 1.5*cm, 1.5*cm, f"Page {doc.page}")

        canvas.restoreState()

    # --------------------------------------------------------------
    # UTILITAIRES
    # --------------------------------------------------------------
    def _chip(self, text, bg_color="#1a3a5c"):
        tbl = Table([[Paragraph(text, self.styles["Chip"])]])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg_color)),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return tbl

    def _plot_to_image(self, fig, width=14*cm):
        img_bytes = pio.to_image(fig, format="png", scale=2)
        bio = BytesIO(img_bytes)
        img = Image(bio)
        img._restrictSize(width, 10*cm)
        return img

    def _table_from_df(self, df, max_rows=12):
        df = df.copy().head(max_rows)
        data = [list(df.columns)] + df.values.tolist()
        tbl = Table(data, hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f4f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0dcea")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return tbl

    # --------------------------------------------------------------
    # PAGES
    # --------------------------------------------------------------
    def _page_garde(self, story):
        # Logo
        if self.logo_path and os.path.exists(self.logo_path):
            img = Image(str(self.logo_path))
            img._restrictSize(6*cm, 6*cm)
            story.append(Spacer(1, 2*cm))
            story.append(img)
            story.append(Spacer(1, 1*cm))
        else:
            story.append(Spacer(1, 3*cm))

        # Titre
        story.append(Paragraph("RPLS – Répertoire des logements locatifs des bailleurs sociaux", self.styles["TitreSection"]))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"Analyse territoriale détaillée", self.styles["SousTitre"]))
        story.append(Spacer(1, 0.8*cm))

        # Territoire
        story.append(Paragraph(f"<b>Territoire :</b> {self.territoire_label}", self.styles["Texte"]))
        story.append(Paragraph(f"<b>Département :</b> {self.dep_code}", self.styles["Texte"]))
        story.append(Paragraph(f"<b>Date de génération :</b> {datetime.date.today().strftime('%d/%m/%Y')}", self.styles["Texte"]))
        story.append(Spacer(1, 0.8*cm))

        story.append(Paragraph(
            "Ce rapport est généré automatiquement à partir du Répertoire des logements locatifs des bailleurs sociaux (RPLS). "
            "Il fournit une vision synthétique et détaillée du parc social sur le territoire sélectionné.",
            self.styles["Texte"]
        ))

        story.append(Spacer(1, 2*cm))
        story.append(Paragraph("Source : RPLS – URSSAF / DHUP", self.styles["Texte"]))
        story.append(PageBreak())

    def _page_synthese(self, story):
        n_logts = len(self.df)
        nb_epci = self.df["EPCI_CODE"].nunique() if "EPCI_CODE" in self.df.columns else "—"
        nb_com = self.df["DEPCOM"].nunique() if "DEPCOM" in self.df.columns else "—"

        story.append(Paragraph("1. Synthèse générale", self.styles["TitreSection"]))
        story.append(Spacer(1, 0.3*cm))

        chips = [
            self._chip(f"{n_logts:,} logements sociaux recensés"),
            self._chip(f"{nb_epci} EPCI distincts" if nb_epci != "—" else "EPCI non renseignés", "#5a7a9c"),
            self._chip(f"{nb_com} communes distinctes" if nb_com != "—" else "Communes non renseignées", "#f9a825"),
        ]
        story.append(Table([[c] for c in chips], hAlign="LEFT", style=TableStyle([("LEFTPADDING", (0,0), (-1,-1), 0)])))
        story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph(
            "Le territoire présente un parc social significatif. Les sections suivantes détaillent la typologie des logements, "
            "les surfaces, les modes de financement, la performance énergétique et l’accessibilité.",
            self.styles["Texte"]
        ))
        story.append(PageBreak())

    def _page_logements(self, story):
        story.append(Paragraph("2. Parc de logements", self.styles["TitreSection"]))
        story.append(Spacer(1, 0.3*cm))

        # Type de construction
        if "TYPECONST_CODE" in self.df.columns:
            df_tc = val_counts_df(self.df["TYPECONST_CODE"], "TYPECONST_LIBELLE", self.df)
            fig_tc = px.bar(
                df_tc.dropna(subset=["Libellé"]),
                x="Nb logements",
                y="Libellé",
                orientation="h",
                color="Nb logements",
                color_continuous_scale=PALETTE_TYPECONST,
                labels={"Libellé": "Type", "Nb logements": "Logements"}
            )
            fig_tc.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                margin=dict(l=0, r=0, t=10, b=10),
                height=400
            )
            story.append(Paragraph("2.1 Typologie de construction", self.styles["SousTitre"]))
            story.append(Spacer(1, 0.2*cm))
            story.append(self._plot_to_image(fig_tc))
            story.append(Spacer(1, 0.2*cm))
            story.append(self._table_from_df(df_tc[["Libellé", "Nb logements", "% total"]]))
            story.append(Spacer(1, 0.4*cm))

        # Nombre de pièces
        if "NBPIECE" in self.df.columns:
            nb = pd.to_numeric(self.df["NBPIECE"], errors="coerce")
            vc_nb = nb.value_counts(dropna=False).sort_index().reset_index()
            vc_nb.columns = ["Nb pièces", "Nb logements"]
            vc_nb["Nb pièces"] = vc_nb["Nb pièces"].fillna("Non renseigné").astype(str)
            vc_nb["% total"] = (vc_nb["Nb logements"] / len(self.df) * 100).round(1).astype(str) + " %"

            fig_np = px.bar(
                vc_nb,
                x="Nb pièces",
                y="Nb logements",
                color="Nb logements",
                color_continuous_scale="Viridis",
                text="Nb logements"
            )
            fig_np.update_layout(margin=dict(l=0, r=0, t=10, b=10), height=350)

            story.append(Paragraph("2.2 Nombre de pièces", self.styles["SousTitre"]))
            story.append(Spacer(1, 0.2*cm))
            story.append(self._plot_to_image(fig_np))
            story.append(Spacer(1, 0.2*cm))
            story.append(self._table_from_df(vc_nb))
            story.append(PageBreak())

    def _page_surfaces(self, story):
        if "SURFHAB" not in self.df.columns:
            return

        surf = pd.to_numeric(self.df["SURFHAB"], errors="coerce").dropna()
        if surf.empty:
            return

        story.append(Paragraph("3. Surfaces habitables", self.styles["TitreSection"]))
        story.append(Spacer(1, 0.3*cm))

        med = surf.median()
        moy = surf.mean()
        smin = surf.min()
        smax = surf.max()

        chips = [
            self._chip(f"Médiane : {med:.0f} m²"),
            self._chip(f"Moyenne : {moy:.0f} m²", "#5a7a9c"),
            self._chip(f"Min : {smin:.0f} m²", "#f9a825"),
            self._chip(f"Max : {smax:.0f} m²", "#2e7d32"),
        ]
        story.append(Table([chips], hAlign="LEFT"))
        story.append(Spacer(1, 0.4*cm))

        tranches = pd.cut(
            surf,
            bins=[0, 30, 50, 70, 90, 110, 999],
            labels=["<30", "30-50", "50-70", "70-90", "90-110", ">110"]
        )
        df_t = tranches.value_counts(sort=False).reset_index()
        df_t.columns = ["Tranche (m²)", "Nb logements"]
        df_t["% total"] = (df_t["Nb logements"] / len(surf) * 100).round(1).astype(str) + " %"

        fig_surf = px.bar(
            df_t,
            x="Tranche (m²)",
            y="Nb logements",
            color="Tranche (m²)",
            color_discrete_sequence=PALETTE_SURF
        )
        fig_surf.update_layout(
            height=300,
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=10)
        )

        story.append(self._plot_to_image(fig_surf))
        story.append(Spacer(1, 0.2*cm))
        story.append(self._table_from_df(df_t))
        story.append(PageBreak())

    def _page_financements(self, story):
        if "FINAN_CODE" not in self.df.columns:
            return

        story.append(Paragraph("4. Financements", self.styles["TitreSection"]))
        story.append(Spacer(1, 0.3*cm))

        df_fin = val_counts_df(self.df["FINAN_CODE"], "FINAN_LIBELLE", self.df)
        fig_fin = px.bar(
            df_fin.dropna(subset=["Libellé"]),
            x="Nb logements",
            y="Libellé",
            orientation="h",
            color="Nb logements",
            color_continuous_scale=PALETTE_FIN,
            labels={"Libellé": "Type de financement", "Nb logements": "Logements"}
        )
        fig_fin.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=10),
            height=400
        )

        story.append(self._plot_to_image(fig_fin))
        story.append(Spacer(1, 0.2*cm))
        story.append(self._table_from_df(df_fin[["Libellé", "Nb logements", "% total"]]))
        story.append(PageBreak())

    def _page_dpe(self, story):
        if "DPEENERGIE" not in self.df.columns:
            return

        story.append(Paragraph("5. Performance énergétique (DPE)", self.styles["TitreSection"]))
        story.append(Spacer(1, 0.3*cm))

        df_dpe = val_counts_df(self.df["DPEENERGIE"], None, self.df)
        df_dpe["Classe"] = df_dpe["Code"]
        df_dpe["% total"] = (df_dpe["Nb logements"] / len(self.df) * 100).round(1).astype(str) + " %"

        fig_dpe = px.bar(
            df_dpe,
            x="Classe",
            y="Nb logements",
            color="Classe",
            color_discrete_map=PALETTE_DPE
        )
        fig_dpe.update_layout(
            height=300,
            showlegend=False,
            margin=dict(l=0, r=0, t=10, b=10)
        )

        story.append(self._plot_to_image(fig_dpe))
        story.append(Spacer(1, 0.2*cm))
        story.append(self._table_from_df(df_dpe[["Classe", "Nb logements", "% total"]]))
        story.append(PageBreak())

    def _page_pmr_qpv(self, story):
        story.append(Paragraph("6. Accessibilité & quartiers prioritaires", self.styles["TitreSection"]))
        story.append(Spacer(1, 0.3*cm))

        # PMR
        if "PMR_CODE" in self.df.columns:
            df_pmr = val_counts_df(self.df["PMR_CODE"], "PMR_LIBELLE", self.df)
            story.append(Paragraph("6.1 Accessibilité PMR", self.styles["SousTitre"]))
            story.append(Spacer(1, 0.2*cm))
            story.append(self._table_from_df(df_pmr[["Libellé", "Nb logements", "% total"]]))
            story.append(Spacer(1, 0.4*cm))

        # QPV
        if "QPV_CODE" in self.df.columns:
            qpv_flag = self.df["QPV_CODE"].notna()
            nb_qpv = qpv_flag.sum()
            part_qpv = nb_qpv / len(self.df) * 100 if len(self.df) > 0 else 0

            story.append(Paragraph("6.2 Quartiers prioritaires (QPV)", self.styles["SousTitre"]))
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(
                f"{nb_qpv:,} logements sont situés en QPV, soit {part_qpv:.1f} % du parc social du territoire.",
                self.styles["Texte"]
            ))

        story.append(PageBreak())

    
    def _page_conclusion(self, story):
        story.append(Paragraph("7. Synthèse et perspectives", self.styles["TitreSection"]))
        story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph(
            "Le présent rapport met en évidence les principales caractéristiques du parc social sur le territoire étudié : "
            "typologie des logements, surfaces, modes de financement, performance énergétique et accessibilité. "
            "Ces éléments constituent une base solide pour alimenter les réflexions stratégiques en matière d’habitat, "
            "de rénovation énergétique et de politique sociale.",
            self.styles["Texte"]
        ))
        story.append(Spacer(1, 0.5*cm))

        story.append(Paragraph(
            "Ce document peut être mobilisé dans le cadre des travaux de planification (SCoT, PLH, PLU(i)), "
            "des conventions avec les bailleurs sociaux, ainsi que pour le suivi des politiques publiques de l’habitat.",
            self.styles["Texte"]
        ))

    # --------------------------------------------------------------
    # BUILD + EXPORT
    # --------------------------------------------------------------
    def build(self):
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            leftMargin=1.8*cm,
            rightMargin=1.8*cm,
            topMargin=2.8*cm,
            bottomMargin=2.0*cm,
            title="RPLS – Rapport territorial"
        )

        story = []
        self._page_garde(story)
        self._page_synthese(story)
        self._page_logements(story)
        self._page_surfaces(story)
        self._page_financements(story)
        self._page_dpe(story)
        self._page_pmr_qpv(story)
        self._page_conclusion(story)

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def get_value(self):
        return self.buffer.getvalue()


# ======================================================================
# GÉOCODEUR BAN — Ultra‑Pro (avec cache)
# ======================================================================

@lru_cache(maxsize=50000)
def geocode_ban(adresse):
    """
    Géocode une adresse via l'API BAN.
    Retourne (lat, lon) ou (None, None).
    """
    try:
        url = "https://api-adresse.data.gouv.fr/search/"
        params = {"q": adresse, "limit": 1}
        r = requests.get(url, params=params, timeout=3)

        if r.status_code != 200:
            return None, None

        data = r.json()
        if not data["features"]:
            return None, None

        coords = data["features"][0]["geometry"]["coordinates"]
        lon, lat = coords[0], coords[1]
        return lat, lon

    except Exception:
        return None, None


def construire_adresse(row):
    """Construit une adresse propre à partir des colonnes RPLS."""
    morceaux = [
        str(row.get("NUMVOIE", "")).strip(),
        str(row.get("TYPVOIE", "")).strip(),
        str(row.get("NOMVOIE", "")).strip(),
        str(row.get("CODEPOSTAL", "")).strip(),
        str(row.get("LIBCOM", "")).strip(),
    ]
    return " ".join([m for m in morceaux if m])


# ======================================================================
# FIX PYINSTALLER — Gestion des chemins _MEIPASS
# ======================================================================
_candidates = [
    getattr(sys, '_MEIPASS', None),
    os.path.dirname(os.path.abspath(__file__)),
    os.path.dirname(sys.executable),
    os.path.join(os.path.dirname(sys.executable), '_internal'),
]
for _p in _candidates:
    if _p and os.path.isdir(os.path.join(_p, 'ui')) and _p not in sys.path:
        sys.path.insert(0, _p)
        break

ROOT_DIR = Path(__file__).resolve().parent

# ======================================================================
# LOGGING ULTRA‑PRO — Fichier logs/app.log
# ======================================================================
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    encoding="utf-8"
)

logging.info("=== Application RPLS Ultra‑Pro démarrée ===")

# ======================================================================
# CONFIG STREAMLIT — Page + UI premium
# ======================================================================
st.set_page_config(
    page_title="RPLS – Logements sociaux (Ultra‑Pro)",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ======================================================================
# CSS PREMIUM — Version Full Combo
# ======================================================================
st.markdown("""
<style>
    .main-title { font-size: 2rem; font-weight: 800; color: #1a3a5c; margin-bottom: 0.2rem; }
    .sub-title { font-size: 1rem; color: #5a7a9c; margin-bottom: 1.5rem; }
    .metric-box { background: #f0f4f9; border-left: 4px solid #1a3a5c; border-radius: 6px; padding: 0.8rem 1.2rem; margin-bottom: 0.5rem; }
    .section-header { font-size: 1.2rem; font-weight: 700; color: #1a3a5c; border-bottom: 2px solid #d0dcea; padding-bottom: 0.3rem; margin: 1.2rem 0 0.8rem 0; }
    .info-chip { display: inline-block; background: #e8f0fe; color: #1a3a5c; border-radius: 12px; padding: 2px 10px; font-size: 0.82rem; margin: 2px; }
    .warn-box { background: #fff8e1; border-left: 4px solid #f9a825; border-radius: 6px; padding: 0.7rem 1rem; font-size: 0.9rem; margin-bottom: 1rem; }
    .success-box { background: #e8f5e9; border-left: 4px solid #2e7d32; border-radius: 6px; padding: 0.7rem 1rem; font-size: 0.9rem; margin-bottom: 1rem; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 18px; border-radius: 8px; background: #eef3f8; color: #1a3a5c !important; font-weight: 600;}
    .stTabs [aria-selected="true"] { background: #1a3a5c !important; color: white !important; }
</style>
""", unsafe_allow_html=True)

# ======================================================================
# CACHE INTELLIGENT — Ultra‑Pro
# ======================================================================

@st.cache_data(show_spinner=False)
def cache_df(df):
    """Cache intelligent pour DataFrame."""
    return df.copy()

@lru_cache(maxsize=64)
def cache_mapping(col_name):
    """Cache pour les mappings value_counts."""
    return col_name


# ======================================================================
# BLOC 2 — CONSTANTES, PALETTES, COLONNES, HELPERS ULTRA‑PRO
# ======================================================================

# ----------------------------------------------------------------------
# PALETTES DE COULEURS — Uniformisation Plotly
# ----------------------------------------------------------------------
PALETTE_DPE = {
    "A": "#009d57", "B": "#33b049", "C": "#bbdb46",
    "D": "#faec19", "E": "#f7b217", "F": "#ef7d1a",
    "G": "#e62224", "N": "#9c9c9c", "Inconnu": "#9c9c9c"
}

PALETTE_QPV = {
    "En QPV": "#f9a825",
    "Hors QPV": "#1a3a5c"
}

PALETTE_PMR = px.colors.qualitative.T10
PALETTE_FIN = px.colors.sequential.Purples
PALETTE_TYPECONST = px.colors.sequential.Blues
PALETTE_SURF = px.colors.sequential.Teal

# ----------------------------------------------------------------------
# COLONNES — Version complète RPLS 2026
# ----------------------------------------------------------------------
COLS_GEO = ["REG_CODE", "REG_LIBELLE", "LIBREG", "DEP_CODE", "DEP_LIBELLE",
            "LIBDEP", "EPCI_CODE", "EPCI_LIBELLE", "LIBEPCI", "DEPCOM",
            "CODEPOSTAL", "LIBCOM"]

COLS_ADRESSE = ["NUMVOIE", "INDREP", "TYPVOIE", "NOMVOIE", "ETAGE",
                "COMPLGEO", "LIEUDIT"]

COLS_QPV = ["QPV_CODE", "QPV_LIBELLE"]

COLS_LOGEMENT = ["DROIT_CODE", "DROIT_LIBELLE", "TYPECONST_CODE",
                 "TYPECONST_LIBELLE", "NBPIECE", "SURFHAB", "CONSTRUCT",
                 "LOCAT", "PATRIMOINE", "ORIGINE"]

COLS_FINANCEMENT = ["FINAN_CODE", "FINAN_LIBELLE", "FINANAUTRE", "CONV",
                    "NUMCONV", "DATCONV", "NEWLOGT_CODE", "NEWLOGT_LIBELLE",
                    "CUS"]

COLS_DPE = ["DPEDATE", "DPEENERGIE", "DPESERRE"]

COLS_SRU = ["SRU_EXPIR", "SRU_ALINEA"]

COLS_PATRIM = ["CODSEGPATRIM", "LIBSEGPATRIM"]

COLS_PMR = ["PMR_CODE", "PMR_LIBELLE"]

COLS_GEO_XY = ["PLG_VOIE", "EPSG", "X", "Y"]

COLS_REF = ["PLG_QP24", "PLG_QP15", "PLG_IRIS2024_CODE",
            "PLG_IRIS2024_LIBELLE", "PLG_ZUS", "PLG_QVA"]

COLS_QUALITE = ["QUALITE_VOIE", "QUALITE_NUMERO", "QUALITE_XY",
                "DISTANCE_PRECISION", "QUALITE_QP24", "QUALITE_QP15",
                "QUALITE_IRIS", "QUALITE_ZUS", "QUALITE_QVA"]

COLS_ZONAGE = ["COMAQP", "COMAZUS", "UU2020", "AAV2020", "ZE2020"]

ALL_COLUMNS = (
    COLS_GEO + COLS_ADRESSE + COLS_QPV + COLS_LOGEMENT +
    COLS_FINANCEMENT + COLS_DPE + COLS_SRU + COLS_PATRIM +
    COLS_PMR + COLS_GEO_XY + COLS_REF + COLS_QUALITE + COLS_ZONAGE
)

# ----------------------------------------------------------------------
# HELPERS ULTRA‑PRO
# ----------------------------------------------------------------------

def log_info(msg: str):
    """Log propre + affichage console Streamlit."""
    logging.info(msg)
    print(msg)

def safe_int(x):
    """Convertit en int sans planter."""
    try:
        return int(x)
    except:
        return None

def safe_float(x):
    """Convertit en float sans planter."""
    try:
        return float(x)
    except:
        return None

def normalize_code(x):
    """Normalise les codes département / commune."""
    if x is None:
        return None
    x = str(x).strip()
    if x.isdigit() and len(x) < 2:
        return x.zfill(2)
    return x

# ----------------------------------------------------------------------
# HELPER — Comptage avec mapping (version ultra‑pro)
# ----------------------------------------------------------------------
def val_counts_df(serie, libelle_col=None, df_source=None, top=20):
    """
    Version ultra‑pro du value_counts :
    - Sécurisée
    - Compatible cache
    - Mapping robuste
    - Tri cohérent
    """
    if serie is None or serie.empty:
        return pd.DataFrame(columns=["Code", "Libellé", "Nb logements", "% total"])

    vc = (
        serie.value_counts(dropna=False)
        .head(top)
        .reset_index()
    )
    vc.columns = ["Code", "Nb logements"]
    vc["Code"] = vc["Code"].astype(str).replace("nan", "Inconnu")

    # Mapping libellé
    if libelle_col and df_source is not None and libelle_col in df_source.columns:
        mapping = (
            df_source[[serie.name, libelle_col]]
            .dropna(subset=[serie.name])
            .drop_duplicates(subset=[serie.name])
            .set_index(serie.name)[libelle_col]
        )
        vc["Libellé"] = vc["Code"].map(mapping).fillna("Inconnu")
    else:
        vc["Libellé"] = vc["Code"]

    # Pourcentage
    if df_source is not None and len(df_source) > 0:
        vc["% total"] = ((vc["Nb logements"] / len(df_source) * 100)
                         .round(1).astype(str) + " %")
    else:
        vc["% total"] = "—"

    return vc


# ======================================================================
# BLOC 3 — CHARGEMENT RPLS (3 Go) ULTRA‑OPTIMISÉ + LOGS + CACHE
# ======================================================================

# ----------------------------------------------------------------------
# Tkinter (optionnel) — Sécurisé pour PyInstaller
# ----------------------------------------------------------------------
HAS_TKINTER = True
try:
    import tkinter as tk
    from tkinter import filedialog
except Exception:
    HAS_TKINTER = False
    log_info("Tkinter indisponible — mode serveur activé.")

def choisir_fichier_local():
    """Sélecteur de fichier local (Tkinter)."""
    if not HAS_TKINTER:
        return None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        fichier = filedialog.askopenfilename(
            title="Sélectionner le fichier RPLS",
            filetypes=[("CSV", "*.csv"), ("Tous les fichiers", "*.*")]
        )
        root.destroy()
        return fichier
    except Exception as e:
        logging.error(f"Erreur Tkinter : {e}")
        return None

# ----------------------------------------------------------------------
# Fonction ULTRA‑PRO de chargement chunké
# ----------------------------------------------------------------------

def detect_dtypes(cols):
    """
    Détection intelligente des dtypes :
    - Les colonnes CODE / DEPCOM / dates → str
    - Le reste → object (sécurisé)
    """
    dtype_schema = {}
    for c in cols:
        if "CODE" in c or c in ["DEPCOM", "DATCONV", "DPEDATE", "CODEPOSTAL"]:
            dtype_schema[c] = "string"
        else:
            dtype_schema[c] = "object"
    return dtype_schema


@st.cache_data(show_spinner=True)
def charger_departement(fichier_path, separateur, encodage, dep_norm):
    """
    Chargement ultra‑pro :
    - Lecture chunkée
    - Filtrage direct sur DEP_CODE
    - Logs détaillés
    - Cache intelligent
    """
    t0 = time.time()
    log_info(f"Chargement du département {dep_norm} depuis {fichier_path}")

    chunks_ok = []
    total_lignes = 0

    try:
        # Lecture de l’en‑tête
        header_df = pd.read_csv(fichier_path, sep=separateur, encoding=encodage, nrows=0)
        cols_reelles = list(header_df.columns)

        if "DEP_CODE" not in cols_reelles:
            raise ValueError(f"Colonne DEP_CODE absente. Colonnes trouvées : {cols_reelles[:10]}")

        # Colonnes à garder
        cols_a_garder = [c for c in ALL_COLUMNS if c in cols_reelles]
        dtype_schema = detect_dtypes(cols_a_garder)

        # Lecture chunkée
        reader = pd.read_csv(
            fichier_path,
            sep=separateur,
            encoding=encodage,
            usecols=cols_a_garder,
            dtype=dtype_schema,
            chunksize=120_000,
            low_memory=False,
        )

        for chunk in reader:
            total_lignes += len(chunk)

            # Normalisation DEP_CODE
            chunk["DEP_CODE"] = (
                chunk["DEP_CODE"]
                .astype("string")
                .str.strip()
                .str.zfill(2)
            )

            # Filtrage direct
            filtre = chunk[chunk["DEP_CODE"] == dep_norm]
            if not filtre.empty:
                chunks_ok.append(filtre)

        if not chunks_ok:
            log_info(f"Aucune ligne trouvée pour {dep_norm}.")
            return None

        df_final = pd.concat(chunks_ok, ignore_index=True)
        log_info(f"Chargement terminé : {len(df_final):,} lignes (sur {total_lignes:,}) en {time.time() - t0:.1f}s")

        return df_final

    except Exception as e:
        logging.error(f"Erreur chargement : {e}")
        return None


# ======================================================================
# BLOC 4 — SIDEBAR PREMIUM + WORKFLOW COMPLET (ULTRA‑PRO)
# ======================================================================

# ----------------------------------------------------------------------
# Initialisation du session_state (sécurisée)
# ----------------------------------------------------------------------
DEFAULT_SESSION = {
    "df": None,
    "dep_charge": None,
    "fichier_path": "",
    "confirm_quit": False,
    "quitting": False,
}

for k, v in DEFAULT_SESSION.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ----------------------------------------------------------------------
# En‑tête + logo
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
            <h1 class='main-title'>📊 URSSAF – Répertoire des logements locatifs des bailleurs sociaux</h1>
            <div class='sub-title'>
                Version Ultra‑Pro Full Combo — Millésime 2026<br>
                Auteur : Philippe PETIT |
                <a href='mailto:philippe.petit.lafiou@outlook.fr?subject=Plateforme Publique [RPLS]'>Contact</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------------
# Workflow quitter (premium)
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

# ======================================================================
# SIDEBAR — CONTROLES ET PARAMÈTRES DE CHARGEMENT
# ======================================================================
with st.sidebar:
    st.caption("Source : RPLS (mise à jour 3 juin 2026) — URSSAF / DHUP")

    # Documentation locale
    url_doc = ROOT_DIR / "assets" / "documentation_rpls.html"
    if url_doc.exists():
        try:
            with open(url_doc, "r", encoding="utf-8") as f:
                st.download_button(
                    label="🗺️ Télécharger la documentation",
                    data=f.read(),
                    file_name="documentation_rpls.html",
                    mime="text/html",
                )
        except IOError as e:
            st.error(f"⚠️ Impossible de lire la documentation : {e}")
    else:
        st.caption("📄 Documentation locale indisponible.")

    # Lien data.gouv
    url_dido = (
        "https://data.statistiques.developpement-durable.gouv.fr/"
        "dido/api/v1/datafiles/f3c2f2cb-8fb1-40fd-8733-964247744c9a/"
        "csv?millesime=2025-01&withColumnName=true&withColumnDescription=true&withColumnUnit=false"
    )
    st.markdown(f"[🗺️ Télécharger les données sur data.gouv.fr]({url_dido})")

    st.divider()

    # Sélecteur de fichier
    if HAS_TKINTER:
        if st.button("📁 Parcourir"):
            fichier = choisir_fichier_local()
            if fichier:
                st.session_state["fichier_path"] = fichier

    fichier_path = st.text_input(
        "Chemin du fichier local (CSV)",
        value=st.session_state["fichier_path"],
        placeholder="Ex : C:/data/RPLS_2026.csv",
    )

    separateur = st.selectbox("Séparateur", [";", ",", "|", "\t"], index=0)
    encodage = st.selectbox("Encodage", ["latin-1", "utf-8", "cp1252", "utf-8-sig"], index=0)
    dep_choisi = st.text_input(
        "Code département",
        placeholder="Ex : 31, 75, 06 …",
        help="La colonne DEP_CODE sera utilisée pour filtrer."
    )

    # ------------------------------------------------------------------
    # Bouton de chargement
    # ------------------------------------------------------------------
    if st.button("🚀 Charger le département", type="primary", use_container_width=True):
        if not fichier_path:
            st.error("Veuillez saisir le chemin du fichier.")
        elif not os.path.exists(fichier_path):
            st.error(f"Fichier introuvable : `{fichier_path}`")
        elif not dep_choisi.strip():
            st.error("Veuillez saisir un code département.")
        else:
            dep_norm = dep_choisi.strip().zfill(2)

            with st.spinner(f"⏳ Lecture sélective — dépt {dep_norm}…"):
                df_loaded = charger_departement(
                    fichier_path=fichier_path,
                    separateur=separateur,
                    encodage=encodage,
                    dep_norm=dep_norm,
                )

            if df_loaded is None:
                st.error(f"Aucune donnée trouvée pour le département {dep_norm}.")
            else:
                st.session_state.df = df_loaded
                st.session_state.dep_charge = dep_norm
                st.success(f"Département {dep_norm} chargé avec succès !")
                st.rerun()

    # ------------------------------------------------------------------
    # Si aucun DF chargé → on arrête ici
    # ------------------------------------------------------------------
    if st.session_state.df is None:
        st.markdown(
            '<div class="warn-box">👆 Chargez d\'abord un département pour accéder aux analyses.</div>',
            unsafe_allow_html=True
        )
        st.stop()

    # ------------------------------------------------------------------
    # Sélection territoriale (EPCI / Commune)
    # ------------------------------------------------------------------
    st.markdown('<div class="section-header">🔍 Sélection Territoire</div>', unsafe_allow_html=True)

    df_sidebar = st.session_state.df
    if df_sidebar is None:
        st.warning("Aucun département chargé.")
        st.stop()

    mode_filtre = st.radio("Filtrer par :", ["EPCI", "Commune (DEPCOM)"], horizontal=True)

    if mode_filtre == "EPCI":
        if "EPCI_CODE" not in df_sidebar.columns:
            st.warning("Colonne EPCI_CODE absente.")
            st.stop()

        epci_opts = (
            df_sidebar[["EPCI_CODE", "EPCI_LIBELLE"]]
            .dropna(subset=["EPCI_CODE"])
            .drop_duplicates("EPCI_CODE")
            .sort_values("EPCI_LIBELLE")
        )
        epci_opts["label"] = epci_opts["EPCI_CODE"] + " — " + epci_opts["EPCI_LIBELLE"].fillna("?")
        choix_select = st.selectbox("Choisir un EPCI", options=epci_opts["label"].tolist(), index=0)
        code_sel = choix_select.split(" — ")[0]

    else:
        if "DEPCOM" not in df_sidebar.columns:
            st.warning("Colonne DEPCOM absente.")
            st.stop()

        com_opts = (
            df_sidebar[["DEPCOM", "LIBCOM"]]
            .dropna(subset=["DEPCOM"])
            .drop_duplicates("DEPCOM")
            .sort_values("LIBCOM")
        )
        com_opts["label"] = com_opts["DEPCOM"] + " — " + com_opts["LIBCOM"].fillna("?")
        choix_select = st.selectbox("Choisir une commune", options=com_opts["label"].tolist(), index=0)
        code_sel = choix_select.split(" — ")[0]

    st.caption(f"**{len(df_sidebar):,}** logements dans le département")


# ======================================================================
# BLOC 5 — PRÉPARATION DES DATAFRAMES + SÉLECTION TERRITORIALE
# ======================================================================

# Récupération du DF complet (sécurisé)
df_full = st.session_state.df
if df_full is None or len(df_full) == 0:
    st.error("Erreur interne : aucun DataFrame chargé.")
    st.stop()

# Application du filtre territorial
if mode_filtre == "EPCI":
    df_work = df_full[df_full["EPCI_CODE"] == code_sel]
else:
    df_work = df_full[df_full["DEPCOM"] == code_sel]

# Sécurisation
if df_work is None or df_work.empty:
    st.warning("Aucun logement pour cette sélection.")
    st.stop()

# ======================================================================
# MÉTRIQUES PRINCIPALES (ULTRA‑PRO)
# ======================================================================
c1, c2, c3, c4 = st.columns(4)

c1.metric("Logements filtrés", f"{len(df_work):,}")
c2.metric("Département actif", st.session_state.dep_charge)
c3.metric("EPCI distincts", df_full["EPCI_CODE"].nunique() if "EPCI_CODE" in df_full.columns else "—")
c4.metric("Communes distinctes", df_full["DEPCOM"].nunique() if "DEPCOM" in df_full.columns else "—")

st.subheader(f"📊 Analyses — {choix_select}")


# ======================================================================
# BLOC 6 — ONGLETS ULTRA‑PRO (6 SECTIONS)
# ======================================================================

onglets = st.tabs([
    "🏠 Logements",
    "💶 Financements",
    "🌿 DPE",
    "♿ PMR & Territoires",
    "🗺️ Géographie",
    "📋 Tableau brut",
    "📄 Rapport PDF",
    "🗺️ Cartographie"
])

# ======================================================================
# ONGLET 1 — LOGEMENTS
# ======================================================================
with onglets[0]:
    col_a, col_b = st.columns(2)

    # --------------------------------------------------------------
    # Type de construction
    # --------------------------------------------------------------
    with col_a:
        st.subheader("🏠 Type de construction")
        if "TYPECONST_CODE" in df_work.columns:
            df_tc = val_counts_df(df_work["TYPECONST_CODE"], "TYPECONST_LIBELLE", df_work)

            fig_tc = px.bar(
                df_tc.dropna(subset=["Libellé"]),
                x="Nb logements",
                y="Libellé",
                orientation='h',
                color="Nb logements",
                color_continuous_scale=PALETTE_TYPECONST,
                labels={"Libellé": "Type", "Nb logements": "Logements"}
            )
            fig_tc.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                height=300,
                margin=dict(l=0, r=0, t=10, b=10)
            )
            st.plotly_chart(fig_tc, use_container_width=True)
            st.dataframe(df_tc, use_container_width=True, hide_index=True)

        # --------------------------------------------------------------
        # Nombre de pièces
        # --------------------------------------------------------------
        st.subheader("🔢 Nombre de pièces")
        if "NBPIECE" in df_work.columns:
            nb = pd.to_numeric(df_work["NBPIECE"], errors="coerce")
            vc_nb = nb.value_counts(dropna=False).sort_index().reset_index()
            vc_nb.columns = ["Nb pièces", "Nb logements"]
            vc_nb["Nb pièces"] = vc_nb["Nb pièces"].fillna("Non renseigné").astype(str)

            fig_np = px.bar(
                vc_nb,
                x="Nb pièces",
                y="Nb logements",
                color="Nb logements",
                color_continuous_scale="Viridis",
                text="Nb logements"
            )
            fig_np.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_np, use_container_width=True)

    # --------------------------------------------------------------
    # Droit (type de bailleur)
    # --------------------------------------------------------------
    with col_b:
        st.subheader("⚖️ Droit (type de bailleur)")
        if "DROIT_CODE" in df_work.columns:
            df_dr = val_counts_df(df_work["DROIT_CODE"], "DROIT_LIBELLE", df_work)

            fig_dr = px.pie(
                df_dr.dropna(subset=["Libellé"]),
                values="Nb logements",
                names="Libellé",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_dr.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_dr, use_container_width=True)

        # --------------------------------------------------------------
        # Surface habitable
        # --------------------------------------------------------------
        st.subheader("📏 Distribution de la surface habitable (m²)")
        if "SURFHAB" in df_work.columns:
            surf = pd.to_numeric(df_work["SURFHAB"], errors="coerce").dropna()
            if not surf.empty:
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                col_s1.metric("Médiane", f"{surf.median():.0f} m²")
                col_s2.metric("Moyenne", f"{surf.mean():.0f} m²")
                col_s3.metric("Min", f"{surf.min():.0f} m²")
                col_s4.metric("Max", f"{surf.max():.0f} m²")

                tranches = pd.cut(
                    surf,
                    bins=[0, 30, 50, 70, 90, 110, 999],
                    labels=["<30", "30-50", "50-70", "70-90", "90-110", ">110"]
                )
                df_t = tranches.value_counts(sort=False).reset_index()
                df_t.columns = ["Tranche (m²)", "Nb logements"]

                fig_surf = px.bar(
                    df_t,
                    x="Tranche (m²)",
                    y="Nb logements",
                    color="Tranche (m²)",
                    color_discrete_sequence=PALETTE_SURF
                )
                fig_surf.update_layout(
                    height=250,
                    showlegend=False,
                    margin=dict(l=0, r=0, t=10, b=10)
                )
                st.plotly_chart(fig_surf, use_container_width=True)

    st.divider()

    # --------------------------------------------------------------
    # Origine du logement
    # --------------------------------------------------------------
    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("🌱 Origine du logement")
        if "ORIGINE" in df_work.columns:
            df_orig = (
                df_work["ORIGINE"]
                .value_counts(dropna=False)
                .reset_index()
                .rename(columns={"ORIGINE": "Origine", "count": "Nb"})
            )
            df_orig["Origine"] = df_orig["Origine"].fillna("Inconnue")

            fig_orig = px.pie(
                df_orig,
                values="Nb",
                names="Origine",
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_orig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_orig, use_container_width=True)

    # --------------------------------------------------------------
    # Segment patrimonial
    # --------------------------------------------------------------
    with col_d:
        st.subheader("🏢 Segment patrimonial")
        if "CODSEGPATRIM" in df_work.columns:
            df_sp = val_counts_df(df_work["CODSEGPATRIM"], "LIBSEGPATRIM", df_work)
            st.dataframe(df_sp, use_container_width=True, hide_index=True)


# ======================================================================
# ONGLET 2 — FINANCEMENTS
# ======================================================================
with onglets[1]:
    col_a, col_b = st.columns(2)

    # --------------------------------------------------------------
    # Mode de financement
    # --------------------------------------------------------------
    with col_a:
        st.subheader("💶 Mode de financement principal")
        if "FINAN_CODE" in df_work.columns:
            df_fc = val_counts_df(df_work["FINAN_CODE"], "FINAN_LIBELLE", df_work, top=15)

            fig_fin = px.bar(
                df_fc.dropna(subset=["Libellé"]),
                x="Nb logements",
                y="Libellé",
                orientation='h',
                color="Nb logements",
                color_continuous_scale=PALETTE_FIN
            )
            fig_fin.update_layout(
                yaxis={'categoryorder': 'total ascending'},
                showlegend=False,
                height=400,
                margin=dict(l=0, r=0, t=10, b=10)
            )
            st.plotly_chart(fig_fin, use_container_width=True)

    # --------------------------------------------------------------
    # NEWLOGT
    # --------------------------------------------------------------
    with col_b:
        st.subheader("🆕 Statut de construction (NEWLOGT)")
        if "NEWLOGT_CODE" in df_work.columns:
            df_nl = val_counts_df(df_work["NEWLOGT_CODE"], "NEWLOGT_LIBELLE", df_work)

            fig_nl = px.pie(
                df_nl.dropna(subset=["Libellé"]),
                values="Nb logements",
                names="Libellé",
                hole=0.3
            )
            fig_nl.update_layout(height=250, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_nl, use_container_width=True)

        # --------------------------------------------------------------
        # Expiration SRU
        # --------------------------------------------------------------
        st.subheader("⏳ Expiration de l'exonération SRU")
        if "SRU_EXPIR" in df_work.columns:
            df_sru = (
                df_work["SRU_EXPIR"]
                .value_counts(dropna=False)
                .reset_index()
                .rename(columns={"SRU_EXPIR": "Année Expir", "count": "Nb"})
            )
            df_sru["Année Expir"] = df_sru["Année Expir"].fillna("Non applicable")
            st.dataframe(df_sru, use_container_width=True, hide_index=True)

    # --------------------------------------------------------------
    # Évolution des conventions
    # --------------------------------------------------------------
    if "DATCONV" in df_work.columns:
        st.subheader("📈 Évolution des signatures de conventions")
        dc = df_work["DATCONV"].dropna().astype(str)
        if not dc.empty:
            annees = dc.str[:4]
            vc_a = annees.value_counts().sort_index().reset_index()
            vc_a.columns = ["Année", "Nb conventions"]

            fig_line = px.line(
                vc_a,
                x="Année",
                y="Nb conventions",
                markers=True,
                line_shape="spline"
            )
            fig_line.update_traces(line_color='#2e7d32', line=dict(width=3))
            fig_line.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_line, use_container_width=True)


# ======================================================================
# ONGLET 3 — DPE
# ======================================================================
with onglets[2]:
    col_a, col_b = st.columns(2)

    # --------------------------------------------------------------
    # Classe énergie
    # --------------------------------------------------------------
    with col_a:
        st.subheader("⚡ Classe Énergie (DPEENERGIE)")
        if "DPEENERGIE" in df_work.columns:
            vc_e = val_counts_df(df_work["DPEENERGIE"], df_source=df_work)
            vc_e["Code"] = vc_e["Code"].fillna("Inconnu").astype(str).str.upper()
            vc_e = vc_e.set_index("Code").reindex(
                ["A", "B", "C", "D", "E", "F", "G", "Inconnu"],
                fill_value=np.nan
            ).reset_index()

            fig_dpe = px.bar(
                vc_e,
                x="Code",
                y="Nb logements",
                color="Code",
                color_discrete_map=PALETTE_DPE,
                text="Nb logements"
            )
            fig_dpe.update_layout(
                xaxis_title="Classe Énergie",
                yaxis_title="Logements",
                showlegend=False,
                height=350,
                margin=dict(l=0, r=0, t=10, b=10)
            )
            st.plotly_chart(fig_dpe, use_container_width=True)

    # --------------------------------------------------------------
    # Classe GES
    # --------------------------------------------------------------
    with col_b:
        st.subheader("🌿 Classe GES (DPESERRE)")
        if "DPESERRE" in df_work.columns:
            vc_g = val_counts_df(df_work["DPESERRE"], df_source=df_work)
            vc_g["Code"] = vc_g["Code"].fillna("Inconnu").astype(str).str.upper()
            vc_g = vc_g.set_index("Code").reindex(
                ["A", "B", "C", "D", "E", "F", "G", "Inconnu"],
                fill_value=np.nan
            ).reset_index()

            fig_ges = px.bar(
                vc_g,
                x="Code",
                y="Nb logements",
                color="Code",
                color_discrete_sequence=px.colors.sequential.YlGnBu_r,
                text="Nb logements"
            )
            fig_ges.update_layout(
                xaxis_title="Classe GES",
                yaxis_title="Logements",
                showlegend=False,
                height=350,
                margin=dict(l=0, r=0, t=10, b=10)
            )
            st.plotly_chart(fig_ges, use_container_width=True)

    # --------------------------------------------------------------
    # Logements sans DPE
    # --------------------------------------------------------------
    nb_sans_dpe = df_work["DPEENERGIE"].isna().sum() if "DPEENERGIE" in df_work.columns else 0
    pct_sans = (nb_sans_dpe / len(df_work) * 100) if len(df_work) > 0 else 0
    st.info(f"💡 **{nb_sans_dpe:,}** logements n'ont pas de classe énergie renseignée ({pct_sans:.1f} %)")


# ======================================================================
# ONGLET 4 — PMR & TERRITOIRES
# ======================================================================
with onglets[3]:
    col_a, col_b = st.columns(2)

    # --------------------------------------------------------------
    # PMR
    # --------------------------------------------------------------
    with col_a:
        st.subheader("♿ Accessibilité PMR")
        if "PMR_CODE" in df_work.columns:
            df_pmr = val_counts_df(df_work["PMR_CODE"], "PMR_LIBELLE", df_work)
            df_pmr["Libellé"] = df_pmr["Libellé"].fillna("Non renseigné")

            fig_pmr = px.pie(
                df_pmr,
                values="Nb logements",
                names="Libellé",
                color_discrete_sequence=PALETTE_PMR
            )
            fig_pmr.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_pmr, use_container_width=True)
        else:
            st.info("Colonne PMR_CODE absente.")

    # --------------------------------------------------------------
    # QPV
    # --------------------------------------------------------------
    with col_b:
        st.subheader("🏘️ Inclusion en Quartiers Prioritaires (QPV)")
        if "QPV_CODE" in df_work.columns:
            nb_qpv = df_work["QPV_CODE"].notna().sum()
            nb_hors = df_work["QPV_CODE"].isna().sum()

            df_qpv_pie = pd.DataFrame({
                "Zone": ["En QPV", "Hors QPV"],
                "Nombre": [nb_qpv, nb_hors]
            })

            fig_qpv = px.pie(
                df_qpv_pie,
                values="Nombre",
                names="Zone",
                color="Zone",
                color_discrete_map=PALETTE_QPV,
                hole=0.5
            )
            fig_qpv.update_layout(height=220, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_qpv, use_container_width=True)

            if nb_qpv > 0 and "QPV_LIBELLE" in df_work.columns:
                df_qpv_list = (
                    df_work[df_work["QPV_CODE"].notna()][["QPV_CODE", "QPV_LIBELLE"]]
                    .value_counts()
                    .reset_index()
                )
                df_qpv_list.columns = ["Code", "Libellé QPV", "Logements"]
                st.dataframe(df_qpv_list, use_container_width=True, hide_index=True)


# ======================================================================
# ONGLET 5 — GÉOGRAPHIE
# ======================================================================
with onglets[4]:
    st.subheader("📍 Répartition du parc par commune")

    if "DEPCOM" in df_work.columns and "LIBCOM" in df_work.columns:
        df_com_rep = (
            df_work.groupby(["DEPCOM", "LIBCOM"], as_index=False)
            .size()
            .sort_values("size", ascending=False)
        )

        fig_geo = px.bar(
            df_com_rep.head(20),
            x="size",
            y="LIBCOM",
            orientation='h',
            color="size",
            color_continuous_scale="Blues"
        )
        fig_geo.update_layout(
            height=500,
            yaxis={'categoryorder': 'total ascending'},
            margin=dict(l=0, r=0, t=10, b=10)
        )
        st.plotly_chart(fig_geo, use_container_width=True)

        st.dataframe(df_com_rep, use_container_width=True, hide_index=True)


# ======================================================================
# ONGLET 6 — TABLEAU BRUT
# ======================================================================
with onglets[5]:
    st.subheader("📋 Tableau brut (données filtrées)")
    st.dataframe(df_work, use_container_width=True)


# ======================================================================
# ONGLET — RAPPORT PDF (Ultra‑Pro Full Combo)
# ======================================================================
with onglets[6]:
    st.subheader("📄 Rapport PDF — Analyse territoriale complète")
    st.info("Génération d’un rapport institutionnel premium basé sur les données filtrées.")

    if st.button("🧾 Générer le rapport PDF", type="primary"):
        with st.spinner("📄 Génération du rapport PDF…"):
            logo_path = ROOT_DIR / "assets" / "logo.png"
            builder = PDFBuilder(
                df=df_work,
                territoire_label=choix_select,
                dep_code=st.session_state.dep_charge,
                logo_path=str(logo_path) if logo_path.exists() else None
            )
            builder.build()
            pdf_bytes = builder.get_value()

        st.success("✅ Rapport généré avec succès.")
        st.download_button(
            label="📥 Télécharger le rapport PDF",
            data=pdf_bytes,
            file_name=f"RPLS_Rapport_{st.session_state.dep_charge}_{datetime.date.today().isoformat()}.pdf",
            mime="application/pdf"
        )

        st.success("✅ Rapport PDF premium généré avec succès.")

# ======================================================================
# ONGLET — CARTOGRAPHIE FOLIUM (Lambert93 → WGS84)
# ======================================================================

with onglets[7]:

    st.subheader("🗺️ Cartographie interactive des logements")

    # Copie du DF
    df_geo = df_work.copy()

    # Conversion X/Y en float
    df_geo["X"] = pd.to_numeric(df_geo["X"], errors="coerce")
    df_geo["Y"] = pd.to_numeric(df_geo["Y"], errors="coerce")

    # Suppression des lignes sans coordonnées
    df_geo = df_geo.dropna(subset=["X", "Y"])

    if df_geo.empty:
        st.warning("Aucune coordonnée exploitable pour la cartographie.")
        st.stop()

    # Conversion Lambert93 → WGS84
    import pyproj
    proj = pyproj.Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)

    df_geo["lon"], df_geo["lat"] = proj.transform(
        df_geo["X"].values,
        df_geo["Y"].values
    )

    # Vérification
    st.write("Aperçu conversion :", df_geo[["X", "Y", "lat", "lon"]].head())

    # Centre de la carte
    lat_center = df_geo["lat"].mean()
    lon_center = df_geo["lon"].mean()

    # Fond de carte
    fond = st.selectbox(
        "Fond de carte",
        ["OpenStreetMap", "CartoDB Positron", "Stamen Toner", "Stamen Terrain"]
    )

    # Carte Folium
    from streamlit_folium import st_folium
    import folium
    from folium.plugins import MarkerCluster

    m = folium.Map(location=[lat_center, lon_center], zoom_start=13, tiles=fond)
    cluster = MarkerCluster().add_to(m)

    # Ajout des points
    for _, row in df_geo.iterrows():
        popup_html = f"""
        <b>Adresse :</b> {row.get('NUMVOIE','')} {row.get('TYPVOIE','')} {row.get('NOMVOIE','')}<br>
        <b>Commune :</b> {row.get('LIBCOM','')}<br>
        <b>Type :</b> {row.get('TYPECONST_LIBELLE','—')}<br>
        <b>DPE :</b> {row.get('DPEENERGIE','—')}<br>
        <b>PMR :</b> {row.get('PMR_LIBELLE','—')}
        """

        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="blue", icon="home", prefix="fa")
        ).add_to(cluster)

    # Affichage
    st_folium(m, width=1200, height=650)

    st.success(f"Carte générée avec {len(df_geo):,} logements géolocalisés.")



# ======================================================================
# BLOC 8 — FOOTER + SORTIE PROPRE (ULTRA‑PRO)
# ======================================================================

st.divider()

# Footer premium
st.markdown(
    """
    <div style='text-align:center; padding:20px; color:#5a7a9c; font-size:0.9rem;'>
        <p><strong>Plateforme RPLS — Version Ultra‑Pro Full Combo</strong></p>
        <p>Développée par Philippe PETIT — Open‑Source & Optimisée</p>
        <p>© 2026 — URSSAF / DHUP — Données publiques</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Sortie propre (si jamais un état de sortie est déclenché ailleurs)
if st.session_state.get("quitting", False):
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