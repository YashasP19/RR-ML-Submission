"""Builds reports/SupeRR_Selector_Season2_Round1_Methodology_Report.pdf from the pipeline's result files.

Usage:  python scripts/build_report.py
Requires: reportlab, matplotlib, adjustText
"""
import csv
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from adjustText import adjust_text
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, Image, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
REP = os.path.join(ROOT, "reports")
FIG = os.path.join(REP, "figures")
OUT = os.path.join(REP, "SupeRR_Selector_Season2_Round1_Methodology_Report.pdf")
LOGO = os.path.join(REP, "assets", "rr-logo.png")
os.makedirs(FIG, exist_ok=True)

BLUE = colors.HexColor("#254AA5")
PINK = colors.HexColor("#E91E8C")
NAVY = colors.HexColor("#0B1B4D")
INK = colors.HexColor("#2B3860")
MUTED = colors.HexColor("#66729A")
LINE = colors.HexColor("#E3E7F3")
SOFT = colors.HexColor("#F4F6FC")
PW, PH = A4
W = PW - 80  # usable width


# ---------------------------------------------------------------- data
def load_all(kind):
    with open(os.path.join(RES, f"players_{kind}.csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


bat_all, bowl_all = load_all("batters"), load_all("bowlers")
bat, bowl = bat_all[:10], bowl_all[:10]
M = json.load(open(os.path.join(RES, "metrics.json")))
ratio = M["swing"]["pressure"] / M["swing"]["normal"]


def sgn(v, d=1):
    v = float(v)
    return f"{'+' if v > 0 else ''}{v:.{d}f}"


# ---------------------------------------------------------------- figures
def make_figures():
    pink, blue, grey = "#E91E8C", "#254AA5", "#C9D0E6"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})

    # Figure 1: top-10 chance
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6))
    for ax, rows, title, col in ((axes[0], bat, "Batters", pink), (axes[1], bowl, "Bowlers", blue)):
        names = [f"{r['Rank']}. {r['player_name']}" for r in rows][::-1]
        vals = [float(r["p_top10_uncond"]) * 100 for r in rows][::-1]
        ax.barh(names, vals, color=col, height=0.62)
        for y, v in enumerate(vals):
            ax.text(v + 1.5, y, f"{v:.0f}%", va="center", fontsize=8, color="#0B1B4D")
        ax.set_xlim(0, 112)
        ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color="#0B1B4D")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(left=False)
        ax.set_xlabel("Share of 500 resamples in which the player stays in the top 10 (%)", fontsize=7.5, color="#66729A")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "top10_chance.png"), dpi=200)
    plt.close(fig)

    # Figure 2: where the top 10 sit among all eligible players
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3))
    panels = ((axes[0], bat_all, "delta_rae", "p_rae100", "Elevation (RAE per 100: pressure minus normal)", "RAE per 100 pressure balls", "Batters", pink),
              (axes[1], bowl_all, "delta_rse", "p_rse_ov", "Elevation (RSE per over: pressure minus normal)", "RSE per over on pressure balls", "Bowlers", blue))
    for ax, rows, xk, yk, xl, yl, title, col in panels:
        ax.scatter([float(r[xk]) for r in rows], [float(r[yk]) for r in rows], s=18, color=grey, zorder=2)
        top = rows[:10]
        ax.scatter([float(r[xk]) for r in top], [float(r[yk]) for r in top], s=34, color=col, zorder=3, edgecolor="white", linewidth=0.6)
        texts = [ax.text(float(r[xk]), float(r[yk]), r["player_name"].split()[-1], fontsize=6.8, color="#0B1B4D", zorder=4) for r in top]
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color="#9AA5C8", lw=0.5))
        ax.axvline(0, color="#9AA5C8", lw=0.7, ls="--", zorder=1)
        ax.set_xlabel(xl, fontsize=7.5, color="#66729A")
        ax.set_ylabel(yl, fontsize=7.5, color="#66729A")
        ax.set_title(f"{title}: top 10 (coloured) among all eligible players", loc="left", fontsize=9.5, fontweight="bold", color="#0B1B4D")
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "landscape.png"), dpi=200)
    plt.close(fig)


make_figures()


# ---------------------------------------------------------------- styles
body = ParagraphStyle("body", fontName="Helvetica", fontSize=9.6, leading=14, textColor=INK, spaceAfter=5, allowWidows=0, allowOrphans=0)
small = ParagraphStyle("small", parent=body, fontSize=8.3, leading=11.5, textColor=MUTED, spaceBefore=5, spaceAfter=8)
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=NAVY, spaceBefore=16, spaceAfter=8, keepWithNext=1)
h1x = ParagraphStyle("h1x", parent=h1, fontSize=26, leading=30, spaceAfter=14)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=BLUE, spaceBefore=10, spaceAfter=5, keepWithNext=1)
bullet = ParagraphStyle("bullet", parent=body, leftIndent=12, bulletIndent=2, spaceAfter=3)
cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.4, leading=10.6, textColor=INK)
cellb = ParagraphStyle("cellb", parent=cell, fontName="Helvetica-Bold", textColor=NAVY)
cellh = ParagraphStyle("cellh", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)


def P(t, s=body):
    return Paragraph(t, s)


def B(items):
    return [Paragraph(t, bullet, bulletText="•") for t in items]


def table_raw(rows, widths, bold_first=False):
    data = [[Paragraph(str(c), cellh if i == 0 else (cellb if (bold_first and j == 0) else cell)) for j, c in enumerate(r)]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                           ("BACKGROUND", (0, 0), (-1, 0), BLUE)]))
    return t


def table(*a, **k):
    return KeepTogether([table_raw(*a, **k)])


def figure(name, caption):
    path = os.path.join(FIG, name)
    from PIL import Image as PILImage
    w, h = PILImage.open(path).size
    img = Image(path, width=W, height=W * h / w)
    return [KeepTogether([img, P(caption, small)])]


# ---------------------------------------------------------------- vector graphics
def pipeline_diagram():
    steps = ["Scope the data", "Game state\nper ball", "Win probability\nmodel", "Pressure flag\n(top 20%)", "Player metrics\nWPA, RAE, RSE",
             "Shrinkage and\neligibility", "Weighted score", "500-resample\nbootstrap", "Consensus\nranking"]
    bw, bh, gap = 88, 40, 14
    d = Drawing(W, 2 * bh + 34)
    for i, s in enumerate(steps):
        row, col = divmod(i, 5)
        x = col * (bw + gap)
        y = bh + 22 if row == 0 else 0
        d.add(Rect(x, y, bw, bh, rx=6, ry=6, fillColor=BLUE if i != 3 else PINK, strokeColor=None))
        n = len(s.split("\n"))
        for k, line in enumerate(s.split("\n")):
            d.add(String(x + bw / 2, y + bh / 2 + (n - 1) * 5 - k * 11 - 3, line, fontName="Helvetica-Bold", fontSize=7.8,
                         fillColor=colors.white, textAnchor="middle"))
        if col < 4 and i < len(steps) - 1:
            d.add(Line(x + bw, y + bh / 2, x + bw + gap - 2, y + bh / 2, strokeColor=NAVY, strokeWidth=1.2))
            d.add(Polygon([x + bw + gap - 2, y + bh / 2 + 3, x + bw + gap + 2, y + bh / 2, x + bw + gap - 2, y + bh / 2 - 3], fillColor=NAVY, strokeColor=None))
    cx = 4 * (bw + gap) + bw / 2
    d.add(Line(cx, bh + 22, cx, bh + 11, strokeColor=NAVY, strokeWidth=1.2))
    d.add(Line(cx, bh + 11, bw / 2, bh + 11, strokeColor=NAVY, strokeWidth=1.2))
    d.add(Line(bw / 2, bh + 11, bw / 2, bh, strokeColor=NAVY, strokeWidth=1.2))
    d.add(Polygon([bw / 2 - 3, bh + 3, bw / 2, bh - 1, bw / 2 + 3, bh + 3], fillColor=NAVY, strokeColor=None))
    return d


def paired_bars(title, rows, vmax, fmt):
    rh, lw = 27, 170
    d = Drawing(W, len(rows) * rh + 26)
    top = len(rows) * rh
    d.add(String(0, top + 14, title, fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    d.add(Rect(W - 150, top + 13, 8, 8, fillColor=colors.HexColor("#9DB0E0"), strokeColor=None))
    d.add(String(W - 138, top + 14, "Ordinary balls", fontName="Helvetica", fontSize=7.5, fillColor=INK))
    d.add(Rect(W - 66, top + 13, 8, 8, fillColor=PINK, strokeColor=None))
    d.add(String(W - 54, top + 14, "Pressure", fontName="Helvetica", fontSize=7.5, fillColor=INK))
    bar_w = W - lw - 60
    for i, (lab, a, b) in enumerate(rows):
        y = (len(rows) - 1 - i) * rh
        d.add(String(0, y + 10, lab, fontName="Helvetica", fontSize=8.2, fillColor=INK))
        for k, (v, col) in enumerate(((a, colors.HexColor("#9DB0E0")), (b, PINK))):
            yy = y + 14 - k * 11
            d.add(Rect(lw, yy, bar_w * v / vmax, 8, fillColor=col, strokeColor=None))
            d.add(String(lw + bar_w * v / vmax + 4, yy + 1, fmt(v), fontName="Helvetica", fontSize=7.5, fillColor=INK))
    return d


def single_bars(title, rows, vmax=1.0):
    rh, lw = 22, 150
    d = Drawing(W, len(rows) * rh + 22)
    d.add(String(0, len(rows) * rh + 8, title, fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
    bar_w = W - lw - 50
    for i, (lab, v) in enumerate(rows):
        y = (len(rows) - 1 - i) * rh
        d.add(String(0, y + 5, lab, fontName="Helvetica", fontSize=8.2, fillColor=INK))
        d.add(Rect(lw, y + 3, bar_w, 9, fillColor=LINE, strokeColor=None))
        d.add(Rect(lw, y + 3, bar_w * v / vmax, 9, fillColor=BLUE, strokeColor=None))
        d.add(String(lw + bar_w + 6, y + 4, f"{v:.2f}", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    return d


# ---------------------------------------------------------------- canvas drawing
def gradient(c, x, y, w, h, c0, c1, horizontal=False, angle_from=None, extend=False):
    c.saveState()
    p = c.beginPath()
    p.rect(x, y, w, h)
    c.clipPath(p, stroke=0, fill=0)
    if horizontal:
        c.linearGradient(x, y, x + w, y, (c0, c1), (0, 1), extend=False)
    else:
        x0, y0, x1, y1 = angle_from or (x, y + h, x, y)
        c.linearGradient(x0, y0, x1, y1, (c0, c1), (0, 1), extend=extend)
    c.restoreState()


def rounded_logo(c, x, y, size, radius):
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, size, size, radius)
    c.clipPath(p, stroke=0, fill=0)
    c.drawImage(ImageReader(LOGO), x, y, size, size)
    c.restoreState()


def cover_page(c, doc):
    c.saveState()
    # full-bleed diagonal gradient, pink at the top-left to royal blue at the bottom-right
    c.setFillColor(BLUE)
    c.rect(0, 0, PW, PH, stroke=0, fill=1)
    gradient(c, 0, 0, PW, PH, PINK, BLUE, angle_from=(0, PH, PW * 0.9, PH * 0.1), extend=True)
    # decorative translucent circles
    c.setFillColor(colors.white)
    for cx, cy, r, a in ((PW - 40, PH - 120, 190, 0.10), (PW - 150, PH - 330, 110, 0.07), (40, 250, 160, 0.06), (PW * 0.7, 120, 90, 0.08)):
        c.setFillAlpha(a)
        c.circle(cx, cy, r, stroke=0, fill=1)
    c.setFillAlpha(1)
    # logo tile and kicker
    rounded_logo(c, 48, PH - 150, 96, 18)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(162, PH - 96, "SUPERR SELECTOR SEASON 2  |  ROUND 1")
    c.setFont("Helvetica", 10)
    c.drawString(162, PH - 114, "Methodology report")
    # title
    c.setFont("Helvetica-Bold", 38)
    for i, line in enumerate(("Identifying the Most", "Reliable Players", "Under Pressure", "in T20 Cricket")):
        c.drawString(48, PH - 300 - i * 46, line)
    c.setFillColor(colors.HexColor("#FFE3F1"))
    c.setFont("Helvetica", 12.5)
    for i, line in enumerate(("A win-probability approach to rating batters and bowlers in high-pressure",
                              "moments, using IPL and full-member T20I data from 2022 onwards.")):
        c.drawString(48, PH - 512 - i * 18, line)
    # stat cards
    stats = (("761", "matches analysed"), (f"{M['deliveries']:,}", "deliveries scored"), (f"{ratio:.1f}x", "larger swing on pressure balls"),
             (str(M["bootstrapResamples"]), "bootstrap resamples"))
    cw, gap = (PW - 96 - 3 * 10) / 4, 10
    for i, (v, t) in enumerate(stats):
        x = 48 + i * (cw + gap)
        c.setFillColor(colors.white)
        c.setFillAlpha(0.16)
        c.roundRect(x, 165, cw, 70, 10, stroke=0, fill=1)
        c.setFillAlpha(1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 21)
        c.drawString(x + 12, 203, v)
        c.setFont("Helvetica", 8.2)
        words = t.split()
        mid = len(words) // 2 if len(t) > 22 else len(words)
        c.drawString(x + 12, 185, " ".join(words[:mid]))
        if mid < len(words):
            c.drawString(x + 12, 174, " ".join(words[mid:]))
    # link pills
    for y, label, url in ((58, "Live dashboard", "https://rr-pressure-players.onrender.com"),
                          (26, "Code and results", "https://github.com/YashasP19/RR-ML-Submission")):
        wl, wu = stringWidth(label, "Helvetica-Bold", 9), stringWidth(url, "Helvetica", 9)
        c.setFillColor(colors.white)
        c.setFillAlpha(0.20)
        c.roundRect(48, y, wl + wu + 38, 24, 12, stroke=0, fill=1)
        c.setFillAlpha(1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(48 + 14, y + 8, label)
        c.setFont("Helvetica", 9)
        c.drawString(48 + 14 + wl + 10, y + 8, url)
    c.restoreState()


def content_page(c, doc):
    c.saveState()
    # top: gradient strip, logo tile, running title
    gradient(c, 0, PH - 10, PW, 10, PINK, BLUE, horizontal=True)
    rounded_logo(c, 40, PH - 40, 22, 5)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(70, PH - 31, "PRESSURE PLAYERS")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawRightString(PW - 40, PH - 31, "SupeRR Selector Season 2  |  Round 1")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.line(40, PH - 47, PW - 40, PH - 47)
    # bottom: thin gradient rule, title, page number badge
    gradient(c, 40, 41, PW - 80, 2, PINK, BLUE, horizontal=True)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.8)
    c.drawString(40, 24, "Identifying the Most Reliable Players Under Pressure in T20 Cricket")
    c.setFillColor(PINK)
    c.circle(PW - 49, 28, 11, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(PW - 49, 25, str(doc.page))
    c.restoreState()


PARTS = {1: ("The Answer", "What we found and the data behind it"),
         2: ("The Method", "How pressure is defined and players are rated"),
         3: ("The Evidence", "Top 10 results, reliability and uncertainty"),
         4: ("Limits and Reproducibility", "Where the model is less certain and how to rerun it")}
CURRENT = {"part": 1}
PAGES = {}
SECTIONS = [(1, "1", "Summary"), (1, "2", "Data and scope"), (1, "3", "Pipeline overview"),
            (2, "4", "Win probability model"), (2, "5", "Defining pressure"),
            (2, "6", "Does the pressure flag work?"), (2, "7", "Measuring players"),
            (2, "8", "Fair comparisons and the final score"),
            (3, "9", "Evidence for the top 10"), (3, "10", "Performance by competition"), (3, "11", "Reliability and robustness"),
            (4, "12", "Limitations"), (4, "13", "Reproducibility and deployment")]


class SetPart(Flowable):
    """Zero-size flowable that records which chapter the next divider page belongs to."""
    def __init__(self, n):
        super().__init__()
        self.n = n

    def wrap(self, aw, ah):
        CURRENT["part"] = self.n
        return (0, 0)

    def draw(self):
        pass


def divider_page(c, doc):
    n = CURRENT["part"]
    title, sub = PARTS[n]
    c.saveState()
    c.setFillColor(PINK)
    c.rect(0, 0, PW, PH, stroke=0, fill=1)
    gradient(c, 0, 0, PW, PH, BLUE, PINK, angle_from=(0, PH, PW, 0), extend=True)
    c.setFillColor(colors.white)
    for cx, cy, r, a in ((PW - 60, PH - 80, 170, 0.09), (60, 120, 150, 0.07), (PW * 0.5, PH * 0.5, 260, 0.05)):
        c.setFillAlpha(a)
        c.circle(cx, cy, r, stroke=0, fill=1)
    c.setFillAlpha(1)
    c.setFillColor(colors.HexColor("#FFE3F1"))
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(PW / 2, PH / 2 + 62, f"PART {n}")
    c.setFillColor(colors.white)
    size = 44 if len(title) < 20 else 32
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(PW / 2, PH / 2 + 8, title)
    c.setStrokeColor(colors.white)
    c.setLineWidth(2.2)
    c.line(PW / 2 - 36, PH / 2 - 14, PW / 2 + 36, PH / 2 - 14)
    c.setFont("Helvetica", 13)
    c.drawCentredString(PW / 2, PH / 2 - 42, sub)
    rounded_logo(c, PW / 2 - 28, 70, 56, 12)
    c.restoreState()


def divider(n):
    """Chapter transitions: no separate title pages, just a sensible break before each part."""
    return {1: [PageBreak()], 2: [], 3: [], 4: []}[n]


class ReportDoc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name == "h1":
            text = f.getPlainText()
            key = f"sec{self.seq.nextf('sec')}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, 0, 0)
            PAGES[text] = self.page



def story():
    S = [NextPageTemplate("content"), PageBreak()]

    # ---------------------------------------------------------------- contents page (pills)
    tocnum = ParagraphStyle("tocnum", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=PINK)
    toctxt = ParagraphStyle("toctxt", fontName="Helvetica", fontSize=11, leading=14, textColor=NAVY)
    tocpg = ParagraphStyle("tocpg", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=BLUE, alignment=2)
    partlab = ParagraphStyle("partlab", fontName="Helvetica-Bold", fontSize=8.5, leading=12, textColor=PINK, spaceBefore=8, spaceAfter=4)
    S += [P("Contents", h1x)]
    for part in (1, 2, 3, 4):
        S.append(Paragraph(f"PART {part}  |  {PARTS[part][0].upper()}", partlab))
        for pp, num, title in SECTIONS:
            if pp != part:
                continue
            pg = PAGES.get(f"{num}. {title}", "-")
            pill = Table([[Paragraph(num, tocnum), Paragraph(title, toctxt), Paragraph(str(pg), tocpg)]], colWidths=[50, W - 50 - 44, 44])
            pill.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                                      ("ROUNDEDCORNERS", [13, 13, 13, 13]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                      ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                                      ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
            S += [pill, Spacer(1, 4)]
    S += divider(1)

    # ---------------------------------------------------------------- 1 summary
    S += [P("1. Summary", h1),
          P("<b>Question.</b> Which batters and bowlers perform best in high-pressure moments, compared with their own usual level?"),
          P("<b>Approach.</b> We estimate the probability of winning on every ball, define pressure as the expected swing in that probability on the next ball, "
            "and rate players on how much they add to winning on pressure balls. Ratings are corrected for small samples, compared with each player's own normal level, "
            "and tested with a 500-resample bootstrap."),
          P("<b>Headline findings</b>")]
    S += B([f"Pressure balls swing win probability <b>{ratio:.1f}x</b> more than ordinary balls ({M['swing']['pressure']:.3f} against {M['swing']['normal']:.3f}).",
            "Ranks 1 to 3 in each list are firm. Ranks 4 to 10 are close and should be read as a group.",
            "Reliability is moderate (0.41 to 0.63 after correction), so we report uncertainty with every player."])
    rows = [["#", "Top 10 batters", "Top 10 bowlers"]] + [[str(i + 1), bat[i]["player_name"], bowl[i]["player_name"]] for i in range(10)]
    S += [Spacer(1, 4), P("Final top 10 (consensus order)", h2), table(rows, [28, W / 2 - 14, W / 2 - 14]),
          P("Order is the consensus of the baseline score, the bootstrap median rank and the ranks under other eligibility cut-offs (section 8).", small),]
    S += figure("top10_chance.png", "Figure 1. How often each top-10 player stays in the top 10 across 500 match-level resamples. Higher means a safer place in the list.")
    
    # ---------------------------------------------------------------- 2, 3 data, pipeline
    S += [KeepTogether([P("2. Data and scope", h1),
          P("<b>Sources.</b> Ball-by-ball records, matches, competitions, teams and playing XIs."),
          P("<b>Scope.</b> All IPL matches plus T20Is in which both teams are among the 12 ICC full members (India, Australia, England, Pakistan, South Africa, New Zealand, "
            "West Indies, Sri Lanka, Bangladesh, Zimbabwe, Afghanistan, Ireland), from 1 January 2022. Weaker opposition inflates statistics, so this keeps the comparison like with like."),
          table_raw([["Item", "Value"], ["Matches in the files", "883"], ["Matches kept", "761 (362 IPL, 399 full-member T20Is)"],
                 ["Deliveries scored", "180,345 (172,812 legal balls)"], ["True dot balls", "60,427"]], [W * 0.4, W * 0.6], bold_first=True)]),
          Spacer(1, 6), P("<b>Cleaning and cricket accounting</b>")]
    S += B(["Abandoned and no-result matches and super overs are excluded; reduced-over matches use the revised overs and targets.",
            "Wides and no-balls are charged to the bowler. Byes and leg-byes are not charged to the bowler and are not counted as dot balls.",
            "Wides are not balls faced by the batter; no-balls are. Run-outs are not credited to the bowler.",
            "Batter runs reconcile exactly with the raw data (checked by an assertion)."])
    S += [Spacer(1, 6), P("3. Pipeline overview", h1), pipeline_diagram(),
          P("Each box is one module in the project (<font face='Courier'>rr_pressure/</font>). The pink box is the definition at the centre of the method.", small)]
    S += divider(2)

    # ---------------------------------------------------------------- 4, 5 model, pressure
    S += [P("4. Win probability model", h1),
          P("Pressure is about how much a ball can change who wins, so every ball needs a win probability. We fit one model for the first innings and one for the chase.")]
    S += B(["<b>Innings 1 inputs:</b> balls remaining, wickets in hand, runs, run rate, difference from the venue's average first-innings score "
            "(the match being scored is left out of that average), and competition type.",
            "<b>Innings 2 inputs:</b> balls remaining, wickets in hand, runs needed, required run rate, rate by wickets lost, and runs per ball needed.",
            "<b>Algorithm:</b> gradient-boosted trees with sigmoid calibration, averaged over two seeds.",
            "<b>Validation:</b> 5-fold outer and 3-fold inner cross-validation, always grouped by match, with an assertion that no match appears in both training and validation."])
    S += [Spacer(1, 4),
          KeepTogether([table_raw([["Out-of-fold score", "Innings 1", "Innings 2", "Overall"], ["Brier score", "0.227", "0.132", "0.181"], ["Log loss", "0.646", "0.406", "0.531"]],
                [W * 0.34, W * 0.22, W * 0.22, W * 0.22], bold_first=True),
          P("By phase the Brier score is 0.156 in the death overs, 0.175 in the middle overs and 0.210 in the powerplay. The chase model is accurate. "
            "First-innings early states are hard to judge, so the pressure cut-off is set separately for each innings.", small)]),
          KeepTogether([P("5. Defining pressure", h1),
          P("<b>Leverage before each ball</b> is the average absolute change in win probability across four possible outcomes (dot, one run, boundary, wicket), "
            "weighted by how often each happens in that phase."),
          table_raw([["Phase", "Dot", "Run", "Boundary", "Wicket"], ["Powerplay (overs 1-6)", "44.4%", "28.9%", "22.1%", "4.5%"],
                 ["Middle (overs 7-15)", "31.0%", "48.5%", "15.7%", "4.8%"], ["Death (overs 16-20)", "29.9%", "40.0%", "21.6%", "8.5%"]],
                [W * 0.36, W * 0.16, W * 0.16, W * 0.16, W * 0.16], bold_first=True)]),
          Spacer(1, 4),
          P("<b>Rule.</b> The top 20% of legal balls in each innings are pressure balls. The flag also applies to wides and no-balls bowled in those states (22.8% of them), "
            "so a bowler's pressure economy is not flattered by leaving extras out."),
          P("<b>Why this definition.</b> Fixed rules such as \"death overs\" or \"required rate above 10\" treat a hopeless chase like a tight one. "
            "Expected swing counts only balls where the result can still move, and it applies equally to batting, bowling and both innings.")]

    # ---------------------------------------------------------------- 6 evidence flag, 7 measuring
    S += [P("6. Does the pressure flag work?", h1),
          paired_bars("Average win-probability swing per ball", [("Average swing", M["swing"]["normal"], M["swing"]["pressure"])], 0.04, lambda v: f"{v:.3f}"),
          Spacer(1, 6),
          paired_bars("Situation profile (share of legal balls)",
                      [("In contests at 25-75% win probability", M["profile"]["closeContest"][0], M["profile"]["closeContest"][1]),
                       ("In overs 16 to 20", M["profile"]["deathOvers"][0], M["profile"]["deathOvers"][1])], 1.0, lambda v: f"{v * 100:.0f}%"),
          Spacer(1, 6)]
    S += B([f"Pressure balls swing win probability <b>{ratio:.1f}x</b> more (0.031 against 0.011).",
            "82% of pressure balls are in close contests (25% to 75% win probability), against 62% of ordinary balls.",
            "Only 0.6% of pressure balls are nearly decided (win probability under 5% or over 95%), so lost causes are excluded.",
            "Mean required rate in chases is 10.3 on pressure balls against 11.5 on ordinary balls, because ordinary balls include hopeless chases.",
            "A simple rule-based pressure index correlated only 0.09 with the swing, which shows fixed rules would capture little of it."])
    S += [P("<b>Plain description.</b> Pressure here means a close contest with a lot still to play for, weighted toward the death overs."),
          P("7. Measuring players", h1),
          P("<b>Win probability added (WPA).</b> The change in win probability caused by a ball goes to the batter, and its negative to the bowler. "
            "First-innings final-ball transitions use the post-delivery state, and per-innings WPA is asserted to add up to the change in win probability."),
          P("<b>Runs above expected (RAE) and runs saved above expected (RSE).</b> A gradient-boosted expected-runs model, out-of-fold and grouped by match, "
            "predicts each ball's runs from the match state. Actual minus expected is RAE for batters; expected minus conceded is RSE for bowlers. "
            "The model is centred (mean expected 1.411 and mean actual 1.411 on legal balls)."),
          table([["", "Batters", "Bowlers"],
                 ["Impact on winning", "WPA per 100 balls", "WPA per over"],
                 ["Against the situation", "RAE per 100 balls", "RSE per over"],
                 ["Raw rate", "Strike rate", "Economy and true dot-ball %"],
                 ["Consistency", "Share of innings (5+ pressure balls) with positive WPA", "Share of spells (6+ legal balls) with positive WPA"],
                 ["Elevation", "Pressure RAE minus normal RAE", "Pressure RSE minus normal RSE"]],
                [W * 0.22, W * 0.39, W * 0.39], bold_first=True)]

    # ---------------------------------------------------------------- 8 fair comparisons
    S += [P("8. Fair comparisons and the final score", h1), P("Fair comparisons", h2)]
    S += B(["<b>Eligibility.</b> At least 150 pressure balls for batters (76 eligible) and 250 for bowlers (31 eligible).",
            "<b>Shrinkage.</b> Empirical Bayes pulls small samples toward the pool average, with a prior of 120 balls (batters) or 150 balls (bowlers), "
            "scaled up for samples under 350 or 450 balls. Consistency uses a beta-binomial prior of 10 innings.",
            "<b>Elevation.</b> Each player is compared with their own normal level, so the rating rewards stepping up, not only being good everywhere.",
            "<b>IPL and T20Is together.</b> The models include a competition flag and the pool is limited to full members. Player splits by competition are in section 10.",
            "<b>Different contexts.</b> Each innings has its own model and threshold, reduced-over matches use revised overs and targets, and venue par removes scoring-environment differences."])
    S += [KeepTogether([P("Scoring", h2),
          table_raw([["Component", "Batter weight", "Component", "Bowler weight"],
                 ["WPA per 100 balls", "35%", "Inverse economy", "30%"], ["RAE per 100 balls", "25%", "WPA per over", "25%"],
                 ["Elevation (RAE)", "20%", "True dot-ball %", "20%"], ["Strike rate", "10%", "Elevation (RSE)", "15%"],
                 ["Consistency", "10%", "Consistency", "10%"]], [W * 0.3, W * 0.2, W * 0.3, W * 0.2])]),
          Spacer(1, 4),
          P("Each component is shrunk, standardised (z-score) and combined with these weights to give the baseline score."),
          P("Consensus ranking", h2)]
    S += B(["The final rank averages three percentile ranks: the baseline score rank, the bootstrap median rank, and the mean rank under other eligibility cut-offs "
            "(batters 100, 200 and 250 balls; bowlers 150, 200 and 300 balls).",
            "A player eligible in under 75% of resamples cannot be in the top 3, and under 70% cannot be in the top 10.",
            "This is why Sunil Narine, 2nd on the baseline score but eligible in under 70% of resamples, is not in the final bowler list."])
    S += divider(3)

    # ---------------------------------------------------------------- 9 evidence
    brow = [["#", "Player", "Balls", "Strike rate", "RAE/100", "Elevation", "Top-10 chance"]]
    for r in bat:
        brow.append([r["Rank"], r["player_name"], r["p_balls"].split(".")[0], f"{float(r['p_sr']):.1f}", f"{float(r['p_rae100']):.1f}",
                     sgn(r["delta_rae"]), f"{float(r['p_top10_uncond']) * 100:.0f}%"])
    S += [KeepTogether([P("9. Evidence for the top 10", h1), P("Batters", h2),
                        table_raw(brow, [22, W * 0.26, W * 0.15, W * 0.12, W * 0.11, W * 0.12, W * 0.14])]), Spacer(1, 4)]
    S += B(["<b>Tim David</b> is the strongest overall batter: the highest WPA per 100 balls (0.95) and a 205.5 IPL pressure strike rate.",
            "<b>Klaasen</b> is second on RAE (36.2) with strong elevation (+16.1).",
            "<b>Abhishek Sharma</b> has the highest RAE (41.9) but an elevation of -2.6: very good everywhere rather than uniquely better under pressure.",
            "<b>Miller, Gill and Prabhsimran Singh</b> fill ranks 8 to 10 with top-10 chances of 23% to 28%. Miller's RAE is low (9.7) and Prabhsimran's WPA per 100 is slightly negative (-0.13)."])
    wrow = [["#", "Player", "Balls", "Econ", "Dot %", "WPA/over", "RSE/over", "Elevation", "Top-10"]]
    for r in bowl:
        wrow.append([r["Rank"], r["player_name"], r["p_balls"].split(".")[0], f"{float(r['p_econ']):.2f}", f"{float(r['p_dot_pct']):.1f}",
                     f"{float(r['p_wpa_ov']):.3f}", sgn(r["p_rse_ov"], 2), sgn(r["delta_rse"], 2), f"{float(r['p_top10_uncond']) * 100:.0f}%"])
    S += [KeepTogether([P("Bowlers", h2), table_raw(wrow, [22, W * 0.22, W * 0.12, W * 0.08, W * 0.09, W * 0.11, W * 0.1, W * 0.11, W * 0.09])]), Spacer(1, 4)]
    S += B(["<b>Hazlewood</b> is the most stable pick: a 95% top-10 chance and the best true dot-ball rate (48.0%).",
            "<b>Bumrah</b> saves the most runs per over among the top four (RSE 1.51), although he saves slightly fewer under pressure than in normal play (elevation -0.36).",
            "<b>Hosein, Kuldeep and Siraj</b> have positive elevation, meaning they are better under pressure than in ordinary play."])
    S += figure("landscape.png", "Figure 2. The top 10 (coloured) among all eligible players. The right of the dashed line means better under pressure than in normal play; higher means more runs above or saved against expectation on pressure balls.")
    S += [Spacer(1, 4)]

    # ---------------------------------------------------------------- 10 competition split
    S += [KeepTogether([P("10. Performance by competition", h1),
          P("Pressure balls and strike rate (batters) or economy (bowlers) in the IPL and in full-member T20Is. The split was computed for the players in the baseline top 10; "
            "it is not available for Miller, Gill, Prabhsimran Singh and Boult.", body),
          P("Batters", h2),
          table_raw([["Player", "IPL balls", "IPL strike rate", "T20I balls", "T20I strike rate"],
                 ["Tim David", "164", "205.5", "205", "174.1"], ["Heinrich Klaasen", "268", "199.3", "36", "144.4"],
                 ["Abhishek Sharma", "206", "177.2", "214", "198.1"], ["Cameron Green", "157", "188.5", "92", "162.0"],
                 ["Daryl Mitchell", "27", "133.3", "156", "182.1"], ["Yashasvi Jaiswal", "217", "170.5", "86", "181.4"],
                 ["Rinku Singh", "175", "173.1", "60", "181.7"]], [W * 0.28, W * 0.15, W * 0.21, W * 0.15, W * 0.21], bold_first=True)]),
      KeepTogether([P("Bowlers", h2),
          table_raw([["Player", "IPL balls", "IPL economy", "T20I balls", "T20I economy"],
                 ["Josh Hazlewood", "235", "7.56", "121", "6.40"], ["Akeal Hosein", "26", "5.31", "326", "7.09"],
                 ["Kuldeep Yadav", "246", "7.59", "73", "7.73"], ["Jasprit Bumrah", "288", "7.48", "97", "6.99"],
                 ["Mohammed Siraj", "344", "8.15", "27", "8.89"], ["Rashid Khan", "275", "8.14", "164", "7.13"],
                 ["Varun Chakravarthy", "255", "8.96", "120", "6.15"], ["Kagiso Rabada", "243", "9.93", "90", "7.07"],
                 ["Maheesh Theekshana", "144", "8.42", "220", "7.23"]], [W * 0.28, W * 0.15, W * 0.21, W * 0.15, W * 0.21], bold_first=True),
          P("Some players rest on one competition (for example Mitchell has 27 IPL pressure balls and Hosein 26), which is one reason ranks 4 to 10 are presented as close.", small)]),]

    # ---------------------------------------------------------------- 11 reliability
    S += [P("11. Reliability and robustness", h1),
          single_bars("Split-half reliability (odd against even matches, Spearman-Brown corrected)",
                      [("Batter strike rate", M["reliability"]["batterStrikeRate"]), ("Batter WPA per 100", M["reliability"]["batterWpa"]),
                       ("Bowler economy", M["reliability"]["bowlerEconomy"])]), Spacer(1, 6)]
    S += B(["<b>Weight sensitivity.</b> Alternative weightings keep 8 to 9 of the baseline batter top 10 and 7 to 9 of the baseline bowler top 10, with rank correlation of 0.935 or higher.",
            "<b>Eligibility sensitivity.</b> Re-ranking at other cut-offs keeps between 4 and 10 of the baseline top 10 (batters at 150, 200, 250 balls: 10, 6, 4 of 10; "
            "bowlers at 150, 200, 250, 300 balls: 6, 7, 10, 9 of 10). The lower places depend on the cut-off, which is why the final order is a consensus.",
            "<b>Bootstrap.</b> 500 match-level resamples rerun eligibility, shrinkage, scoring and ranking. Top-10 chance is the share of resamples in which a player stays in the top 10.",
            "<b>Reading rank against top-10 chance.</b> Rank is the consensus order. Top-10 chance only counts in or out, so two neighbouring ranks can have percentages that are close "
            "or reversed (for example Kuldeep 66% and Bumrah 69%). With 500 resamples the margin is about 2 points, so these are effectively tied."])

    # ---------------------------------------------------------------- 12, 13
    S += divider(4)
    S += [P("12. Limitations", h1)]
    S += B(["<b>Opposition strength</b> is not adjusted. All deliveries between full members count equally.",
            "<b>Model-dependent pressure.</b> A different win-probability model could move some names.",
            "<b>First-innings model</b> is weak (Brier 0.227), so first-innings pressure labels are noisier than chase labels.",
            "<b>Moderate reliability.</b> The order within ranks 4 to 10 should be read as close.",
            "<b>Lower batter places.</b> Ranks 8 to 10 have top-10 chances of 23% to 28%.",
            "<b>Elevation</b> partly reflects when a player bats or bowls; using RAE and RSE reduces, but does not remove, this.",
            "<b>Small gaps.</b> About 240 non-striker run-outs are not credited to the non-striker, and the bootstrap holds the win-probability model and pressure threshold fixed.",
            "<b>Thin competition samples</b> exist for some players, for example Mitchell (27 IPL pressure balls)."])
    S += [P("13. Reproducibility and deployment", h1)]
    S += B(["<b>Code.</b> A modular Python package with one stage per module (data, game state, win probability, pressure, expected runs, batters, bowlers, bootstrap, "
            "validation, consensus) and a narrated notebook (<font face='Courier'>Final_v2.ipynb</font>).",
            "<b>Determinism.</b> A single scikit-learn model family, fixed seeds, folds grouped by match. Rerunning the modular pipeline gave results identical to the notebook.",
            "<b>Dashboard.</b> A Flask app with a JSON API on Render: https://rr-pressure-players.onrender.com (rankings, searchable player table, method and evidence).",
            "<b>Run it.</b> <font face='Courier'>python run_pipeline.py --data-dir data --out-dir results</font>"])





    return S


def build_pdf():
    doc = ReportDoc(OUT, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=62, bottomMargin=52,
                    title="Identifying the Most Reliable Players Under Pressure in T20 Cricket", author="Yashas P",
                    subject="SupeRR Selector Season 2, Round 1 methodology report")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[Frame(0, 0, 20, 20, id="c", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=cover_page),
        PageTemplate(id="content", frames=[Frame(40, 52, W, PH - 114, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=content_page),
        PageTemplate(id="divider", frames=[Frame(0, 0, 20, 20, id="d", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=divider_page),
    ])
    doc.build(story())


build_pdf()  # first pass records section pages
build_pdf()  # second pass fills the contents pills
print("wrote", OUT)
