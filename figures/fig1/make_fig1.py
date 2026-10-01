"""
Fig. 1 for the NeuroVFM Matters Arising (Nature Medicine), styled to match our
figure kit: 183 mm double column, Arial/Helvetica 5 to 7 pt, 8 pt bold lowercase
panel letters, 0.5 pt rules, one hue per meaning, PNG at 600 dpi plus SVG with
editable text.

Usage:
  python make_fig1.py --curve A2_sens_vs_flagrate.csv --scores decoding_miss_scores.csv \
                      --case cq500_inset.png --out fig1
  --curve  : columns flag_rate, sensitivity (optional sens_lo, sens_hi), GPT-5 primary run
  --scores : column score, one row per decoding miss (classifier score on the missed finding)
  --case   : PNG of the panel-a inset slice (CQ500, public)

Any missing input is drawn as a synthetic stand-in, framed in dashed yellow and
listed in a corner stamp, so placeholders cannot slip into a submission.

Colour meanings (fixed across the figure):
  blue       classifier readout and every classifier score
  vermillion report readout and the misses it causes
  greys      structure, perception and reasoning misses
"""
import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Rectangle
from scipy.stats import norm

# ============================================================================ numbers
# Final summary numbers (GPT-5 primary screener, N = 472, 206 urgent)
N, N_URGENT = 472, 206
PROSE_FLAG, PROSE_SENS = 34.1, 73.3                    # percent
AUROC, AUROC_CI = 0.949, (0.928, 0.967)
DSENS, DSENS_CI = 0.0, (-2.9, 3.0)                     # percentage points
DECOMP = [("Decoding", 40), ("Perception", 10), ("Reasoning", 5)]
MEDIAN_SCORE = 0.93
NONE_NAMED = (38, 40)

# Panel a inset text. These mirror {{FIG1A_*}} in the legend. Fill in together.
CASE_FINDING = "Subarachnoid hemorrhage"
CASE_SCORE = 0.99                                      # CQ500-CT-303 (SAH decoding miss, 0.999)
CASE_REPORT = "Study is unremarkable."
CASE_CONFIRMED = True                                  # SAH conspicuous at slice 70 (basal cisterns)

# ============================================================================ style
MM = 1 / 25.4
W, H = 183, 112
INK, SUB, RULE = "#1a1a1a", "#5c5c5c", "#9a9a9a"
BOX, BOX_EDGE = "#f1f2f4", "#c9ccd1"
ENC = "#4f5a67"                                        # shared encoder, neutral slate
CLS, CLS_FILL = "#0072B2", "#e5f0f8"                   # classifier (Okabe-Ito blue)
RPT, RPT_FILL = "#D55E00", "#fbe9df"                   # report path (Okabe-Ito vermillion)
PER, REA = "#9e9e9e", "#d4d4d4"                        # perception, reasoning misses
FLAG = "#FFD24D"                                       # placeholder marker, as in Figs 3 and 4
FS, FS_S, FS_T, FS_L, LW = 6.0, 5.0, 7.0, 8.0, 0.5

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS_S, "ytick.labelsize": FS_S,
    "axes.linewidth": LW, "xtick.major.width": LW, "ytick.major.width": LW,
    "xtick.major.size": 2, "ytick.major.size": 2, "xtick.major.pad": 1.5,
    "ytick.major.pad": 1.5, "axes.labelpad": 2, "axes.spines.top": False,
    "axes.spines.right": False, "axes.edgecolor": INK, "text.color": INK,
    "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
    "svg.fonttype": "none", "pdf.fonttype": 42, "legend.frameon": False,
})
PLACEHOLDERS = []

# ============================================================================ mm helpers
fig = plt.figure(figsize=(W * MM, H * MM))
CV = fig.add_axes([0, 0, 1, 1], zorder=0)              # mm canvas, y runs downward
CV.set_xlim(0, W); CV.set_ylim(H, 0); CV.axis("off")


def ax_mm(x, y, w, h):
    return fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H], zorder=2)


def T(x, y, s, fs=FS, **kw):
    kw.setdefault("va", "center")
    kw.setdefault("ha", "left")
    return CV.text(x, y, s, fontsize=fs, zorder=20, linespacing=1.25, **kw)


def box(x, y, w, h, fc=BOX, ec=BOX_EDGE, stack=1, lw=LW, dashed=False, r=1.0):
    for i in reversed(range(stack)):
        CV.add_patch(FancyBboxPatch(
            (x + 0.9 * i, y - 0.9 * i), w, h, boxstyle=f"round,pad=0,rounding_size={r}",
            fc=fc, ec=ec, lw=lw, ls=(0, (3, 2)) if dashed else "-",
            alpha=1.0 if i == 0 else 0.55, zorder=3 + stack - i))


def arrow(p0, p1, color=SUB, head=True, dashed=False):
    CV.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle="-|>,head_length=2.2,head_width=1.2" if head else "-",
        lw=LW, color=color, ls=(0, (3, 2)) if dashed else "-",
        shrinkA=0, shrinkB=0, zorder=2))


def letter(x, y, s, title):
    T(x, y, s, fs=FS_L, weight="bold", va="top")
    T(x + 4.5, y + 0.45, title, fs=FS_T, va="top")


def flag_axes(ax, what):
    ax.add_patch(Rectangle((0, 0), 1, 1, transform=ax.transAxes, fill=False, ec=FLAG,
                           lw=0.75, ls=(0, (3, 2)), clip_on=False, zorder=10))
    PLACEHOLDERS.append(what)


# ============================================================================ a
def panel_a(case_png):
    letter(0, 0, "a", "One encoder, two readouts")
    ycls, yrpt = 13, 37                                 # row centres (mm)

    box(2, 19, 14, 12, stack=3)
    T(9, 25, "Head CT", ha="center")
    arrow((18.6, 25), (23, 25))
    box(23, 14, 18, 22, fc=ENC, ec=ENC, stack=2)
    T(32, 25, "Frozen\nNeuroVFM\nencoder", ha="center", color="white", weight="bold")

    # fork: one trunk, two branches
    CV.plot([41, 45], [25, 25], color=SUB, lw=LW, zorder=2)
    CV.plot([45, 45], [ycls, yrpt], color=SUB, lw=LW, zorder=2)
    arrow((45, ycls), (49.5, ycls))
    arrow((45, yrpt), (49.5, yrpt))

    # classifier row
    box(50, ycls - 5, 29, 10, fc=CLS_FILL, ec=CLS)
    T(64.5, ycls - 1.4, "Diagnostic classifier", ha="center", color=CLS, weight="bold")
    T(64.5, ycls + 1.9, "0.95M parameters", ha="center", color=SUB, fs=FS_S)
    arrow((79.5, ycls), (84, ycls))
    heights = [0.92, 0.15, 0.08, 0.55, 0.05, 0.22, 0.10, 0.04, 0.30, 0.07, 0.12]
    for k, hh in enumerate(heights):
        CV.add_patch(Rectangle((85 + 1.6 * k, ycls + 3.5 - 7 * hh), 1.1, 7 * hh,
                               fc=CLS, ec="none", zorder=5))
    CV.plot([84.6, 102.6], [ycls + 3.5, ycls + 3.5], color=RULE, lw=0.3, zorder=4)
    T(93.6, ycls + 5.6, "scores for 82 diagnoses", ha="center", fs=FS_S, color=SUB)
    arrow((104, ycls), (108.5, ycls))
    T(109.5, ycls, "Triage score\n(this analysis)", color=CLS, weight="bold")

    # report row
    box(50, yrpt - 5, 29, 10, fc=RPT_FILL, ec=RPT)
    T(64.5, yrpt - 1.4, "Language model", ha="center", color=RPT, weight="bold")
    T(64.5, yrpt + 1.9, "14B parameters", ha="center", color=SUB, fs=FS_S)
    arrow((79.5, yrpt), (84, yrpt))
    box(84, yrpt - 5.5, 12, 11, fc="white", ec=BOX_EDGE)
    for k in range(4):
        CV.plot([85.6, 94.4 - (3 if k == 3 else 0)], [yrpt - 3 + 2 * k] * 2,
                color=RULE, lw=0.6, zorder=6)
    T(90, yrpt + 7.4, "written findings", ha="center", fs=FS_S, color=SUB)
    arrow((96.5, yrpt), (100.5, yrpt))
    box(101, yrpt - 4, 13, 8)
    T(107.5, yrpt, "GPT-5\nscreener", ha="center", fs=FS_S)
    arrow((114.5, yrpt), (118.5, yrpt))
    T(119.5, yrpt, "Acuity\n(original study)", color=RPT, weight="bold")

    # the two readouts never meet
    CV.plot([52, 130], [25, 25], color=RULE, lw=0.4, ls=(0, (2, 2)), zorder=1)
    T(91, 25, " readouts share the encoder but never communicate ", ha="center",
      fs=FS_S, color=SUB, style="italic", backgroundcolor="white")

    # inset case
    ix, iy, iw = 142, 5, 30
    a = ax_mm(ix, iy, iw, iw)
    a.set_axis_off()
    if case_png and os.path.exists(case_png):
        img = plt.imread(case_png)
        img = img[..., :3].mean(-1) if img.ndim == 3 else img
        a.imshow(img, cmap="gray", interpolation="lanczos")
    else:
        yy, xx = np.mgrid[-1:1:256j, -1:1:256j]
        r = (xx / 0.74) ** 2 + (yy / 0.9) ** 2
        img = np.where(r < 1, 1.0, 0.0) * 0.95
        img[r < 0.86] = 0.42
        img[((xx + 0.38) / 0.17) ** 2 + ((yy + 0.05) / 0.13) ** 2 < 1] = 0.8
        img += 0.03 * np.random.default_rng(2).standard_normal(img.shape)
        a.imshow(np.clip(img, 0, 1), cmap="gray", interpolation="lanczos")
        flag_axes(a, "inset slice")
    a.text(0.04, 0.5, "R", transform=a.transAxes, color="white", alpha=0.8,
           fontsize=FS_S, va="center")
    a.text(0.96, 0.5, "L", transform=a.transAxes, color="white", alpha=0.8,
           fontsize=FS_S, va="center", ha="right")
    T(ix + iw / 2, iy + iw + 3.2, f"Classifier, {CASE_FINDING.lower()}: {CASE_SCORE:.2f}",
      ha="center", fs=FS_S, color=CLS, weight="bold")
    T(ix + iw / 2, iy + iw + 6.6, f"Report: “{CASE_REPORT}”", ha="center",
      fs=FS_S, color=RPT, weight="bold")
    if not CASE_CONFIRMED:
        PLACEHOLDERS.append("inset text")


# ============================================================================ b
def synthetic_curve():
    """Binormal stand-in with the reported AUROC, used only when --curve is missing."""
    a = np.sqrt(2) * norm.ppf(AUROC)
    fpr = np.linspace(0, 1, 400)
    sens = norm.cdf(a + norm.ppf(np.clip(fpr, 1e-6, 1 - 1e-6)))
    p = N_URGENT / N
    flag = p * sens + (1 - p) * fpr
    return 100 * flag, 100 * sens, None, None


def panel_b(curve_csv):
    letter(0, 52, "b", "Triage by each readout")
    ax = ax_mm(13, 60, 44, 40)
    if curve_csv and os.path.exists(curve_csv):
        import pandas as pd
        d = pd.read_csv(curve_csv).sort_values("flag_rate")
        sc = 100 if d.sensitivity.max() <= 1 else 1
        x, y = sc * d.flag_rate.values, sc * d.sensitivity.values
        lo = sc * d.sens_lo.values if "sens_lo" in d else None
        hi = sc * d.sens_hi.values if "sens_hi" in d else None
    else:
        x, y, lo, hi = synthetic_curve()
        flag_axes(ax, "curve")
    if lo is not None and hi is not None:
        ax.fill_between(x, lo, hi, color=CLS, alpha=0.15, lw=0)
    ax.plot(x, y, color=CLS, lw=1.0, solid_capstyle="round", zorder=3)

    ax.plot([PROSE_FLAG] * 2, [0, PROSE_SENS], color=RULE, lw=0.4, ls=(0, (2, 2)), zorder=1)
    ax.plot(PROSE_FLAG, PROSE_SENS, "o", ms=4.2, mfc=RPT, mec="white", mew=0.6, zorder=5)
    ax.text(PROSE_FLAG + 1.5, 3, "matched\nflag rate", fontsize=FS_S, color=SUB, va="bottom")

    # direct labels in place of a legend
    ax.text(52, 86, "Classifier score", color=CLS, weight="bold", fontsize=FS_S, va="top")
    ax.annotate("Written findings\nread by GPT-5", (PROSE_FLAG, PROSE_SENS),
                xytext=(PROSE_FLAG + 12, PROSE_SENS - 16), fontsize=FS_S, color=RPT,
                weight="bold", va="center",
                arrowprops=dict(arrowstyle="-", lw=0.3, color=RPT, shrinkB=2.5))
    ax.text(99, 20, f"AUROC {AUROC:.3f}\n({AUROC_CI[0]:.3f}–{AUROC_CI[1]:.3f})",
            ha="right", va="bottom", fontsize=FS, color=CLS, weight="bold", linespacing=1.2)

    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100]); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Studies flagged (%)")
    ax.set_ylabel("Sensitivity for urgent studies (%)")
    ax.set_aspect("auto")


# ============================================================================ c
def swarm(vals, dx, dy):
    """Deterministic one-sided-free beeswarm offsets."""
    placed, ys = [], []
    for v in vals:
        for k in range(60):
            y = (k + 1) // 2 * dy * (1 if k % 2 else -1)
            if all(abs(v - pv) >= dx or abs(y - py) >= dy for pv, py in placed):
                break
        placed.append((v, y)); ys.append(y)
    return np.array(ys)


def panel_c():
    letter(50, 52, "c", "Where the readouts disagree")
    x0, y0, cw, ch = 60, 66, 14, 11                     # grid origin + cell size (mm)
    val = {(0, 0): "134", (0, 1): "17", (1, 0): "17", (1, 1): "38"}
    fillc = {(0, 0): "#b7adea", (0, 1): CLS_FILL, (1, 0): RPT_FILL, (1, 1): "#ededea"}
    edgec = {(0, 0): "#5a4fcf", (0, 1): CLS, (1, 0): RPT, (1, 1): PER}
    for ri in (0, 1):
        for ci in (0, 1):
            x, y = x0 + ci * cw, y0 + ri * ch
            CV.add_patch(Rectangle((x, y), cw, ch, fc=fillc[(ri, ci)], ec=edgec[(ri, ci)],
                                   lw=LW, zorder=4))
            T(x + cw / 2, y + ch / 2, val[(ri, ci)], ha="center", va="center",
              fs=FS_T, weight="bold", color=edgec[(ri, ci)])
    # column headers (report)
    T(x0 + cw, y0 - 3.4, "Report", ha="center", fs=FS_S, color=RPT, weight="bold")
    T(x0 + cw / 2, y0 - 1.2, "flag", ha="center", fs=FS_S, color=SUB)
    T(x0 + cw + cw / 2, y0 - 1.2, "miss", ha="center", fs=FS_S, color=SUB)
    # row headers (classifier)
    T(x0 - 3.4, y0 + ch, "Classifier", ha="center", fs=FS_S, color=CLS, weight="bold",
      rotation=90, va="center")
    T(x0 - 1.0, y0 + ch / 2, "flag", ha="right", fs=FS_S, color=SUB)
    T(x0 - 1.0, y0 + ch + ch / 2, "miss", ha="right", fs=FS_S, color=SUB)
    T(x0 + cw, y0 + 2 * ch + 3.0, "206 urgent studies at the matched flag rate",
      ha="center", fs=FS_S, color=SUB, style="italic")


LIGHT = "#9ec3e6"                                      # classifier score >0.5 but not flagged


def panel_d(scores_csv):
    # one strip of all 55 report misses; letter only, no title (legend explains)
    letter(66, 52, "c", "")
    X0, XW, sy, sh = 72, 103, 64, 30                    # strip box (mm); ~30 mm tall
    ax = ax_mm(X0, sy, XW, sh)
    mp = "misses_55.csv"
    if scores_csv:
        cand = os.path.join(os.path.dirname(scores_csv), "misses_55.csv")
        if os.path.exists(cand): mp = cand
    if os.path.exists(mp):
        import pandas as pd
        df = pd.read_csv(mp)
        score = df["score"].to_numpy(float)
        tobool = lambda c: df[c].astype(str).str.strip().str.lower().isin(["true", "1"]).to_numpy()
        rea, flg = tobool("reasoning"), tobool("flagged")
    else:
        rng = np.random.default_rng(7)
        score = np.concatenate([np.clip(rng.beta(9, .9, 40) * .5 + .5, .5, .999),
                                rng.uniform(0.05, 0.5, 10), rng.uniform(.4, .99, 5)])
        rea = np.array([False] * 50 + [True] * 5)
        flg = (score >= 0.976) & ~rea
        flag_axes(ax, "misses")

    y = swarm(score, dx=0.022, dy=0.17)
    groups = [(~rea & flg, CLS), (~rea & ~flg & (score > 0.5), LIGHT), (~rea & (score <= 0.5), PER)]
    for m, c in groups:
        ax.scatter(score[m], y[m], s=9, c=c, lw=0.3, edgecolors="white", zorder=3)
    ax.scatter(score[rea], y[rea], s=12, facecolors="none", edgecolors=RPT, linewidths=0.8, zorder=4)
    ax.axvline(0.5, color=RULE, lw=0.5, ls=(0, (2, 2)), zorder=1)

    ytop, ybot = float(y.max()), float(y.min())
    hi = ~rea & (score > 0.5); lo = ~rea & (score <= 0.5)
    n_flag, n_hi, n_lo, n_rea = int((~rea & flg).sum()), int(hi.sum()), int(lo.sum()), int(rea.sum())
    hitop = float(y[hi].max()) if hi.any() else ytop
    lotop = float(y[lo].max()) if lo.any() else ytop
    ax.text(0.80, hitop + 0.35, f"report silent, classifier > 0.5  ({n_hi})\n"
            f"{n_flag} flagged at the matched alarm rate", ha="center", va="bottom",
            fontsize=FS_S, color=CLS, linespacing=1.25)
    ax.text(0.25, lotop + 0.35, f"report silent,\nclassifier ≤ 0.5  ({n_lo})",
            ha="center", va="bottom", fontsize=FS_S, color=SUB, linespacing=1.25)
    med = float(np.median(score[hi]))
    ax.plot([med, med], [ybot - 0.3, ybot - 0.85], color=INK, lw=0.9, zorder=4)
    ax.text(med, ybot - 1.02, f"median {med:.2f}", ha="center", va="top", fontsize=FS_S)
    ax.scatter([0.03], [ybot - 1.4], s=12, facecolors="none", edgecolors=RPT,
               linewidths=0.8, zorder=4, clip_on=False)
    ax.text(0.06, ybot - 1.4, f"report named the finding ({n_rea})", ha="left", va="center",
            fontsize=FS_S, color=RPT)

    ax.set_xlim(0, 1); ax.set_ylim(ybot - 1.75, ytop + 1.3)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_bounds(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1]); ax.set_xticklabels(["0", "0.25", "0.50", "0.75", "1"])
    ax.set_xlabel("Classifier score for the missed finding")


# ============================================================================ build
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--curve"); ap.add_argument("--scores"); ap.add_argument("--case")
    ap.add_argument("--out", default="fig1")
    ap.add_argument("--pdf", action="store_true", help="also export PDF for production")
    a = ap.parse_args()

    panel_a(a.case)
    panel_b(a.curve)
    panel_d(a.scores)   # decoding-miss strip, now panel c (2x2 dropped — read as a wash)
    if PLACEHOLDERS:
        T(W - 1, H - 1.2, "PLACEHOLDER: " + ", ".join(PLACEHOLDERS), ha="right",
          va="bottom", fs=FS_S, color="#c99a00", weight="bold")
        print("placeholders:", ", ".join(PLACEHOLDERS))

    exts = ["png", "svg"] + (["pdf"] if a.pdf else [])
    for ext in exts:
        fig.savefig(f"{a.out}.{ext}", dpi=600 if ext == "png" else None, facecolor="white")
    print("saved", [f"{a.out}.{e}" for e in exts])


if __name__ == "__main__":
    main()
