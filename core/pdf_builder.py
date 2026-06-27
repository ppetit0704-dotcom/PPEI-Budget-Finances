# core/pdf_builder.py
"""
Export PDF complet — PPEI-Budget&Finances
ReportLab uniquement (pas de kaleido/plotly pour les graphiques : on génère
des tableaux et barres SVG internes ReportLab).
"""

import io
from datetime import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
BLEU_FONCE  = colors.HexColor("#1a3a5c")
BLEU_MOYEN  = colors.HexColor("#2563a8")
BLEU_CLAIR  = colors.HexColor("#dbeafe")
GRIS_CLAIR  = colors.HexColor("#f1f5f9")
GRIS_TEXTE  = colors.HexColor("#374151")
VERT        = colors.HexColor("#16a34a")
ORANGE      = colors.HexColor("#ea580c")
ROUGE       = colors.HexColor("#dc2626")

W, H = A4


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["titre"] = ParagraphStyle(
        "titre", fontName="Helvetica-Bold", fontSize=18,
        textColor=BLEU_FONCE, spaceAfter=4, alignment=TA_LEFT,
    )
    styles["sous_titre"] = ParagraphStyle(
        "sous_titre", fontName="Helvetica", fontSize=11,
        textColor=BLEU_MOYEN, spaceAfter=12, alignment=TA_LEFT,
    )
    styles["section"] = ParagraphStyle(
        "section", fontName="Helvetica-Bold", fontSize=13,
        textColor=BLEU_FONCE, spaceBefore=14, spaceAfter=6,
    )
    styles["normal"] = ParagraphStyle(
        "normal", fontName="Helvetica", fontSize=9,
        textColor=GRIS_TEXTE, spaceAfter=3,
    )
    styles["small"] = ParagraphStyle(
        "small", fontName="Helvetica", fontSize=8,
        textColor=GRIS_TEXTE,
    )
    styles["entete_table"] = ParagraphStyle(
        "entete_table", fontName="Helvetica-Bold", fontSize=8,
        textColor=colors.white, alignment=TA_CENTER,
    )
    styles["cell"] = ParagraphStyle(
        "cell", fontName="Helvetica", fontSize=8,
        textColor=GRIS_TEXTE,
    )
    styles["cell_right"] = ParagraphStyle(
        "cell_right", fontName="Helvetica", fontSize=8,
        textColor=GRIS_TEXTE, alignment=TA_RIGHT,
    )
    return styles


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt(val, suffix="€") -> str:
    """Formate un float en monnaie FR."""
    try:
        v = float(val)
        if v < 0:
            return f"-{abs(v):,.2f} {suffix}".replace(",", "\u202f")
        return f"{v:,.2f} {suffix}".replace(",", "\u202f")
    except Exception:
        return str(val)


def _pct(val) -> str:
    try:
        return f"{float(val):.1f} %"
    except Exception:
        return "—"


def _table_style_base(header_color=BLEU_MOYEN) -> TableStyle:
    return TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  header_color),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  8),
        ("ALIGN",       (0, 0), (-1, 0),  "CENTER"),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_CLAIR]),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ])


def _header_footer(canvas, doc, budget_label: str, date_export: str):
    canvas.saveState()
    W_, H_ = doc.pagesize
    # Bandeau haut
    canvas.setFillColor(BLEU_FONCE)
    canvas.rect(0, H_ - 1.2*cm, W_, 1.2*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(1*cm, H_ - 0.85*cm, f"PPEI-Budget&Finances  —  {budget_label}")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(W_ - 1*cm, H_ - 0.85*cm, f"Export : {date_export}")
    # Pied
    canvas.setFillColor(BLEU_FONCE)
    canvas.rect(0, 0, W_, 0.8*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1*cm, 0.25*cm, "PPEI — Plateforme Publique d'Échanges et d'Informations")
    canvas.drawRightString(W_ - 1*cm, 0.25*cm, f"Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Génération principale
# ---------------------------------------------------------------------------

def generate_pdf(
    df_sit: pd.DataFrame,
    df_gl: pd.DataFrame,
    budget_label: str,
) -> bytes:
    """
    Génère le PDF complet et retourne les bytes.
    """
    buf = io.BytesIO()
    date_export = datetime.now().strftime("%d/%m/%Y %H:%M")

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.8*cm, bottomMargin=1.5*cm,
        title=f"PPEI-Budget&Finances — {budget_label}",
    )

    S = _styles()
    story = []

    def hf(canvas, doc_):
        _header_footer(canvas, doc_, budget_label, date_export)

    # -----------------------------------------------------------------------
    # PAGE DE GARDE
    # -----------------------------------------------------------------------
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph("PPEI — Budget &amp; Finances", S["titre"]))
    story.append(HRFlowable(width="100%", thickness=2, color=BLEU_MOYEN, spaceAfter=6))
    story.append(Paragraph(f"Budget : <b>{budget_label}</b>", S["sous_titre"]))
    story.append(Paragraph(f"Rapport généré le {date_export}", S["normal"]))
    story.append(Spacer(1, 0.5*cm))

    # Méta-données rapides
    nb_sit = len(df_sit)
    nb_gl  = len(df_gl)
    meta = [
        ["Fichier", "Lignes analysées"],
        ["Situation comptable", str(nb_sit)],
        ["Grand Livre", str(nb_gl)],
    ]
    t = Table(meta, colWidths=[9*cm, 6*cm])
    t.setStyle(_table_style_base())
    story.append(t)
    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 1 — VUE D'ENSEMBLE
    # -----------------------------------------------------------------------
    story.append(Paragraph("1 — Vue d'ensemble", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLEU_CLAIR, spaceAfter=6))

    for section_code, section_label in [("F", "Fonctionnement"), ("I", "Investissement")]:
        df_s = df_sit[df_sit["Section"] == section_code]
        dep  = df_s[df_s["Sens"] == "D"]
        rec  = df_s[df_s["Sens"] == "R"]

        prevu_d = dep["Total_Prévu"].sum()
        real_d  = dep["Réalisé"].sum()
        prevu_r = rec["Total_Prévu"].sum()
        real_r  = rec["Réalisé"].sum()
        taux_d  = (real_d / prevu_d * 100) if prevu_d else 0
        taux_r  = (real_r / prevu_r * 100) if prevu_r else 0

        story.append(Paragraph(f"Section {section_label}", S["normal"]))
        data = [
            ["", "Prévu", "Réalisé", "Taux"],
            ["Dépenses", _fmt(prevu_d), _fmt(real_d), _pct(taux_d)],
            ["Recettes", _fmt(prevu_r), _fmt(real_r), _pct(taux_r)],
        ]
        t = Table(data, colWidths=[4*cm, 4.5*cm, 4.5*cm, 3*cm])
        ts = _table_style_base()
        ts.add("ALIGN", (1, 1), (-1, -1), "RIGHT")
        t.setStyle(ts)
        story.append(t)
        story.append(Spacer(1, 0.4*cm))

    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 2 — FONCTIONNEMENT PAR CHAPITRE
    # -----------------------------------------------------------------------
    story.append(Paragraph("2 — Fonctionnement par chapitre", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLEU_CLAIR, spaceAfter=6))
    _add_chapitre_table(story, df_sit, "F", S)
    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 3 — INVESTISSEMENT PAR CHAPITRE
    # -----------------------------------------------------------------------
    story.append(Paragraph("3 — Investissement par chapitre", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLEU_CLAIR, spaceAfter=6))
    _add_chapitre_table(story, df_sit, "I", S)
    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 4 — ÉVOLUTION N-5
    # -----------------------------------------------------------------------
    story.append(Paragraph("4 — Évolution historique (N-1 à N-5)", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLEU_CLAIR, spaceAfter=6))
    _add_evolution_table(story, df_sit, S)
    story.append(PageBreak())

    # -----------------------------------------------------------------------
    # SECTION 5 — GRAND LIVRE (résumé par tiers)
    # -----------------------------------------------------------------------
    story.append(Paragraph("5 — Grand Livre — Top tiers (Liquidations)", S["section"]))
    story.append(HRFlowable(width="100%", thickness=1, color=BLEU_CLAIR, spaceAfter=6))
    _add_gl_tiers_table(story, df_gl, S)

    # -----------------------------------------------------------------------
    # BUILD
    # -----------------------------------------------------------------------
    doc.build(story, onFirstPage=hf, onLaterPages=hf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Sous-fonctions tableaux
# ---------------------------------------------------------------------------

def _add_chapitre_table(story, df_sit, section_code, S):
    df = df_sit[df_sit["Section"] == section_code].copy()
    for sens_code, sens_label in [("D", "Dépenses"), ("R", "Recettes")]:
        df_s = df[df["Sens"] == sens_code]
        if df_s.empty:
            continue
        agg = (
            df_s.groupby("Chapitre", as_index=False)
            .agg(Prévu=("Total_Prévu", "sum"),
                 Réalisé=("Réalisé", "sum"),
                 Engagé=("Engagé", "sum"))
        )
        agg["Taux"] = agg.apply(
            lambda r: r["Réalisé"] / r["Prévu"] * 100 if r["Prévu"] else 0, axis=1
        )

        story.append(Paragraph(f"<b>{sens_label}</b>", S["normal"]))
        header = ["Chapitre", "Prévu (€)", "Réalisé (€)", "Engagé (€)", "Taux (%)"]
        rows = [header]
        for _, r in agg.iterrows():
            rows.append([
                r["Chapitre"][:55] + ("…" if len(r["Chapitre"]) > 55 else ""),
                _fmt(r["Prévu"], ""),
                _fmt(r["Réalisé"], ""),
                _fmt(r["Engagé"], ""),
                _pct(r["Taux"]),
            ])
        col_w = [8*cm, 3*cm, 3*cm, 2.5*cm, 2*cm]
        t = Table(rows, colWidths=col_w, repeatRows=1)
        ts = _table_style_base()
        ts.add("ALIGN", (1, 1), (-1, -1), "RIGHT")
        t.setStyle(ts)
        story.append(KeepTogether([t]))
        story.append(Spacer(1, 0.4*cm))


def _add_evolution_table(story, df_sit, S):
    annees = ["Liquidé_N_1", "Liquidé_N_2", "Liquidé_N_3", "Liquidé_N_4", "Liquidé_N_5"]
    labels = ["N-1", "N-2", "N-3", "N-4", "N-5"]

    for section_code, section_label in [("F", "Fonctionnement"), ("I", "Investissement")]:
        df_s = df_sit[df_sit["Section"] == section_code]
        story.append(Paragraph(f"<b>Section {section_label}</b>", S["normal"]))
        header = ["Sens"] + labels
        rows = [header]
        for sens_code, sens_label in [("D", "Dépenses"), ("R", "Recettes")]:
            df_ss = df_s[df_s["Sens"] == sens_code]
            row = [sens_label]
            for col in annees:
                if col in df_ss.columns:
                    row.append(_fmt(df_ss[col].sum(), ""))
                else:
                    row.append("—")
            rows.append(row)
        col_w = [3*cm] + [3.2*cm] * 5
        t = Table(rows, colWidths=col_w)
        ts = _table_style_base()
        ts.add("ALIGN", (1, 1), (-1, -1), "RIGHT")
        t.setStyle(ts)
        story.append(t)
        story.append(Spacer(1, 0.4*cm))


def _add_gl_tiers_table(story, df_gl, S):
    df_liq = df_gl[df_gl["type"] == "Liquidation"].copy()
    if df_liq.empty:
        story.append(Paragraph("Aucune liquidation dans le Grand Livre.", S["normal"]))
        return

    agg = (
        df_liq.groupby("Tiers", as_index=False)
        .agg(Montant_TTC=("Montant_TTC", "sum"),
             Nb=("Montant_TTC", "count"))
        .sort_values("Montant_TTC", ascending=False)
        .head(30)
    )

    header = ["Tiers", "Montant TTC (€)", "Nb lignes"]
    rows = [header]
    for _, r in agg.iterrows():
        tiers = str(r["Tiers"])[:40] + ("…" if len(str(r["Tiers"])) > 40 else "")
        rows.append([tiers, _fmt(r["Montant_TTC"], ""), str(int(r["Nb"]))])

    col_w = [9*cm, 4.5*cm, 3*cm]
    t = Table(rows, colWidths=col_w, repeatRows=1)
    ts = _table_style_base()
    ts.add("ALIGN", (1, 1), (-1, -1), "RIGHT")
    t.setStyle(ts)
    story.append(t)
