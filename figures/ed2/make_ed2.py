"""Extended Data Fig. 2 — clinical indication, urgency definition, calibration, prevalence.
Same figure kit as Fig. 1 / ED1. Panels a,b use verified decomposition counts; c,d load
ed2_calib.csv / ed2_reweight.csv computed from the caches. Usage: python make_ed2.py --out ed2
"""
import argparse, csv, os
import numpy as np
import matplotlib.pyplot as plt

DATA = "/project/hipaa_visishslab/neurovfm_triage_audit/outputs/fig1_data"
MM = 1 / 25.4
W, H = 183, 62
INK, SUB, RULE = "#1a1a1a", "#5c5c5c", "#9a9a9a"
CLS, RPT, PER = "#0072B2", "#D55E00", "#9e9e9e"
FS, FS_S, FS_T, FS_L, LW = 6.0, 5.0, 7.0, 8.0, 0.5
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"],
    "font.size": FS, "axes.labelsize": FS, "xtick.labelsize": FS_S, "ytick.labelsize": FS_S,
    "axes.linewidth": LW, "xtick.major.width": LW, "ytick.major.width": LW,
    "xtick.major.size": 2, "ytick.major.size": 2, "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
    "axes.labelpad": 2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": INK, "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK, "svg.fonttype": "none", "pdf.fonttype": 42})

fig = plt.figure(figsize=(W * MM, H * MM))
CV = fig.add_axes([0, 0, 1, 1]); CV.set_xlim(0, W); CV.set_ylim(H, 0); CV.axis("off")
def ax_mm(x, y, w, h): return fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
def letter(x, y, s, t):
    CV.text(x, y, s, fontsize=FS_L, weight="bold", va="top")
    CV.text(x + 4.2, y + 0.4, t, fontsize=FS, va="top")

def stacked(ax, groups, colors):
    xs = np.arange(len(groups)); bottoms = np.zeros(len(groups))
    for ci in range(3):
        vals = np.array([g[1][ci] for g in groups], float)
        ax.bar(xs, vals, bottom=bottoms, width=0.6, color=colors[ci], lw=0, zorder=3)
        for xi, (v, b) in enumerate(zip(vals, bottoms)):
            if v >= 2: ax.text(xs[xi], b + v / 2, f"{int(v)}", ha="center", va="center",
                               fontsize=FS_S, color="white", weight="bold")
        bottoms += vals
    ax.set_xticks(xs); ax.set_xticklabels([g[0] for g in groups])
    ax.set_ylim(0, max(bottoms) * 1.14); ax.set_ylabel("Report-pipeline misses")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="ed2")
    ap.add_argument("--pdf", action="store_true"); a = ap.parse_args()
    colors = [CLS, PER, RPT]

    # a — indication decomposition (verified counts)
    letter(0, 2, "a", "Clinical indication")
    ax = ax_mm(13, 9, 36, 30)
    stacked(ax, [("None\n(55)", (40, 10, 5)), ("Head\ntrauma\n(56)", (40, 10, 6)),
                 ("Head-\nache\n(63)", (47, 11, 5))], colors)
    ax.text(0.5, 1.02, "38 of 40 decoding misses persist", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=FS_S, color=SUB)

    # b — excluded calvarial-only
    letter(52, 2, "b", "Calvarial-only excluded")
    ax = ax_mm(64, 9, 17, 30)
    stacked(ax, [("n = 468\n(51 miss)", (37, 9, 5))], colors)
    ax.set_xlim(-0.7, 0.7)
    ax.text(0.5, 1.02, "Δsens 0.000\nAUROC 0.948", transform=ax.transAxes, ha="center",
            va="bottom", fontsize=FS_S, color=SUB, linespacing=1.2)

    # legend
    for i, (c, lab) in enumerate(zip(colors, ["Decoding", "Perception", "Reasoning"])):
        CV.add_patch(plt.Rectangle((84, 10 + i * 4), 2.2, 2.2, color=c, lw=0))
        CV.text(87.2, 11.1 + i * 4, lab, fontsize=FS_S, va="center")

    # c — reliability diagram
    letter(96, 2, "c", "Calibration")
    ax = ax_mm(108, 9, 30, 30)
    rows = list(csv.DictReader(open(f"{DATA}/ed2_calib.csv")))
    conf = [float(r["conf"]) for r in rows]; acc = [float(r["acc"]) for r in rows]
    ns = [int(r["n"]) for r in rows]
    ax.plot([0, 1], [0, 1], color=RULE, lw=0.6, ls=(0, (2, 2)), zorder=1)
    sizes = [6 + 24 * (n / max(ns)) for n in ns]
    ax.plot(conf, acc, "-", color=CLS, lw=0.8, zorder=2)
    ax.scatter(conf, acc, s=sizes, c=CLS, lw=0.3, edgecolors="white", zorder=3)
    ax.text(0.04, 0.93, "ECE 0.25", transform=ax.transAxes, fontsize=FS_S, color=INK,
            weight="bold", va="top")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_xticks([0, 0.5, 1]); ax.set_yticks([0, 0.5, 1])
    ax.set_xlabel("Mean classifier score"); ax.set_ylabel("Fraction positive")
    ax.set_aspect("equal")

    # d — prevalence reweighting
    letter(144, 2, "d", "Prevalence")
    ax = ax_mm(154, 9, 24, 30)
    rr = list(csv.DictReader(open(f"{DATA}/ed2_reweight.csv")))
    sens = np.array([float(r["sens"]) for r in rr]) * 100
    f13 = np.array([float(r["flag13"]) for r in rr]) * 100
    f44 = np.array([float(r["flag44"]) for r in rr]) * 100
    o44 = np.argsort(f44); o13 = np.argsort(f13)
    ax.plot(f44[o44], sens[o44], color=RULE, lw=0.8, zorder=2)
    ax.plot(f13[o13], sens[o13], color=CLS, lw=1.0, zorder=3)
    ax.text(0.96, 0.30, "13% prev.", transform=ax.transAxes, ha="right", fontsize=FS_S,
            color=CLS, weight="bold")
    ax.text(0.96, 0.12, "44% (CQ500)", transform=ax.transAxes, ha="right", fontsize=FS_S,
            color=SUB)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_xticks([0, 50, 100]); ax.set_yticks([0, 50, 100])
    ax.set_xlabel("Studies flagged (%)"); ax.set_ylabel("Sensitivity (%)")

    exts = ["png", "svg"] + (["pdf"] if a.pdf else [])
    for e in exts:
        fig.savefig(f"{a.out}.{e}", dpi=600 if e == "png" else None, facecolor="white")
    print("saved", [f"{a.out}.{e}" for e in exts])


if __name__ == "__main__":
    main()
