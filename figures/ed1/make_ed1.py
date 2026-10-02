"""
Extended Data Fig. 1 for the NeuroVFM Matters Arising. Decomposition of the 55
report-pipeline misses under alternative definitions and screening models, plus
judge checks. Same figure kit as Fig. 1: 183 mm, Arial 5-7 pt, 0.5 pt rules,
one hue per meaning (blue = classifier/encoder represented the finding,
vermillion = report path, grey = perception). Numbers are recomputed here from
the caches so the figure cannot drift from the text.

Usage: python make_ed1.py --out ed1
"""
import argparse, json, csv
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------------- data (recomputed)
T = "/project/hipaa_visishslab/neurovfm_triage_audit"
C = f"{T}/outputs/cache_path_a"
URG = {"ich": ["intracranial_hemorrhage"], "iph": ["intraparenchymal_hemorrhage"],
       "ivh": ["intraventricular_hemorrhage"], "edh": ["epidural_hematoma"],
       "sah": ["aneurysmal_subarachnoid_hemorrhage", "traumatic_subarachnoid_hemorrhage"],
       "sdh": ["acute_subdural_hematoma", "subacute_chronic_subdural_hematoma"],
       "calvarialfracture": ["displaced_skull_fracture", "nondisplaced_skull_fracture"],
       "masseffect": ["brain_mass_effect"], "midlineshift": ["midline_shift"]}
LBL = {"ich": "Intracranial hemorrhage", "iph": "Intraparenchymal hemorrhage",
       "ivh": "Intraventricular hemorrhage", "edh": "Epidural hematoma",
       "sah": "Subarachnoid hemorrhage", "sdh": "Subdural hematoma",
       "calvarialfracture": "Calvarial fracture", "masseffect": "Mass effect",
       "midlineshift": "Midline shift"}


def ld(p): return {json.loads(l)["study"]: json.loads(l) for l in open(p) if l.strip()}


def compute():
    P = {s: r["probs"] for s, r in ld(f"{C}/path_a_probs.jsonl").items()}
    G = {s: r for s, r in ld(f"{T}/outputs/gpt_cq500/gpt.jsonl").items() if '"error"' not in json.dumps(r)}
    CA = {s: r["acuity"].lower() for s, r in ld(f"{C}/acuity_claude.jsonl").items()}
    CM = {s: r["mentioned"] for s, r in ld(f"{C}/prose_hit_claude.jsonl").items()}

    def tru(v):
        try: return float(v) >= 0.5
        except: return False
    cons = {}; rd = csv.DictReader(open(f"{T}/data/cq500_consensus.csv")); idc = rd.fieldnames[0]
    for r in rd: cons[r[idc].strip()] = {f: tru(r.get(f, 0)) for f in URG if f in r}
    S = [s for s in P if s in cons and s in G]
    pa = lambda s, f: max(P[s].get(l, 0) for l in URG[f])
    urg = lambda s: max(pa(s, f) for f in URG)
    gt = lambda s: any(cons[s].get(f) for f in URG)
    posf = lambda s: [f for f in URG if cons[s].get(f)]
    n = len(S); THR = sorted((urg(s) for s in S), reverse=True)[round(0.341 * n) - 1]
    U = [s for s in S if gt(s)]
    gu = lambda s: G[s].get("acuity", "").lower() == "urgent"
    gma = lambda s: any(G[s].get("mentioned", {}).get(f) for f in posf(s))
    resp = lambda s: pa(s, max(posf(s), key=lambda f: pa(s, f)))

    miss = [s for s in U if not gu(s)]; rea = [s for s in miss if gma(s)]
    rem = [s for s in miss if not gma(s)]
    pri = (sum(resp(s) > 0.5 for s in rem), sum(resp(s) <= 0.5 for s in rem), len(rea))
    mat = (sum(urg(s) >= THR for s in rem), sum(urg(s) < THR for s in rem), len(rea))

    cu = lambda s: CA.get(s, "") == "urgent"
    cma = lambda s: any(CM.get(s, {}).get(f) for f in posf(s))
    cmiss = [s for s in U if not cu(s)]; crea = [s for s in cmiss if cma(s)]
    crem = [s for s in cmiss if not cma(s)]
    cpri = (sum(resp(s) > 0.5 for s in crem), sum(resp(s) <= 0.5 for s in crem), len(crea))
    cmat = (sum(urg(s) >= THR for s in crem), sum(urg(s) < THR for s in crem), len(crea))
    both = [s for s in S if s in CA]
    agree = sum(gu(s) == cu(s) for s in both) / len(both)

    dec = [s for s in rem if resp(s) > 0.5]
    byf = Counter(max(posf(s), key=lambda f: pa(s, f)) for s in dec)

    named_none = lambda s: not any(G[s].get("mentioned", {}).get(f) for f in URG)
    nu = [s for s in S if not gt(s)]
    d_urg = sum(named_none(s) for s in U) / len(U)
    d_nu = sum(named_none(s) for s in nu) / len(nu)

    def kappa(a, b):
        m = len(a); po = sum(x == y for x, y in zip(a, b)) / m
        pa_ = sum(a) / m; pb = sum(b) / m; pe = pa_ * pb + (1 - pa_) * (1 - pb)
        return (po - pe) / (1 - pe) if pe < 1 else 1.0
    ks = []
    for f in URG:
        a = [bool(G[s].get("mentioned", {}).get(f)) for s in both]
        b = [bool(CM.get(s, {}).get(f)) for s in both]
        if sum(a) + sum(b) > 0: ks.append(kappa(a, b))
    # judge (GPT-5) vs rule-based keyword detector, hemorrhage subtypes
    RP = {s: r.get("findings", "") for s, r in ld(f"{T}/outputs/cache_path_a/path_b_triage.jsonl").items()}
    RULE = {"iph": ["intraparenchymal", "intracerebral hemorrhage", "parenchymal hemorrhage"],
            "ivh": ["intraventricular"], "edh": ["epidural", "extradural"],
            "sah": ["subarachnoid"], "sdh": ["subdural"]}
    def rule(s, f): t = RP.get(s, "").lower(); return any(k in t for k in RULE[f])
    kr = []
    for f in RULE:
        a = [bool(G[s].get("mentioned", {}).get(f)) for s in both if s in RP]
        b = [rule(s, f) for s in both if s in RP]
        if sum(a) + sum(b) > 0: kr.append(kappa(a, b))
    return dict(pri=pri, mat=mat, cpri=cpri, cmat=cmat, agree=agree, n_c=len(cmiss),
               byf=byf.most_common(), d_urg=d_urg, d_nu=d_nu, kappa=float(np.mean(ks)),
               krule=float(np.mean(kr)), n_urg=len(U), n_nu=len(nu))


# ---------------------------------------------------------------- style
MM = 1 / 25.4
W, H = 183, 96
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
    "xtick.color": INK, "ytick.color": INK, "svg.fonttype": "none", "pdf.fonttype": 42,
})

fig = plt.figure(figsize=(W * MM, H * MM))
CV = fig.add_axes([0, 0, 1, 1]); CV.set_xlim(0, W); CV.set_ylim(H, 0); CV.axis("off")


def ax_mm(x, y, w, h): return fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])


def letter(x, y, s, title):
    CV.text(x, y, s, fontsize=FS_L, weight="bold", va="top", ha="left")
    CV.text(x + 4.2, y + 0.4, title, fontsize=FS, va="top", ha="left")


def grouped(ax, groups, cats, colors, title_tiers):
    """groups: list of (label, (d,p,r)); draws a stacked bar per group (tier)."""
    xs = np.arange(len(groups)) * 1.0
    bottoms = np.zeros(len(groups))
    for ci, cat in enumerate(cats):
        vals = np.array([g[1][ci] for g in groups], float)
        ax.bar(xs, vals, bottom=bottoms, width=0.62, color=colors[ci], lw=0, zorder=3,
               label=cat)
        for xi, (v, b) in enumerate(zip(vals, bottoms)):
            if v >= 2:
                ax.text(xs[xi], b + v / 2, f"{int(v)}", ha="center", va="center",
                        fontsize=FS_S, color="white", weight="bold")
        bottoms += vals
    ax.set_xticks(xs); ax.set_xticklabels([g[0] for g in groups])
    ax.set_ylim(0, max(bottoms) * 1.12)
    ax.set_ylabel("Report-pipeline misses")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="ed1")
    ap.add_argument("--pdf", action="store_true"); a = ap.parse_args()
    D = compute()
    cats = ["Decoding", "Perception", "Reasoning"]
    colors = [CLS, PER, RPT]

    # a — GPT-5 screener, two definitions
    letter(0, 2, "a", "GPT-5 screener")
    ax = ax_mm(13, 9, 40, 32)
    grouped(ax, [("Primary\n(score > 0.5)", D["pri"]), ("Matched\nthreshold", D["mat"])],
            cats, colors, None)
    ax.set_title("55 misses", fontsize=FS_S, color=SUB, pad=2)

    # b — Claude screener (sensitivity)
    letter(62, 2, "b", "Claude screener")
    ax = ax_mm(75, 9, 40, 32)
    grouped(ax, [("Primary\n(score > 0.5)", D["cpri"]), ("Matched\nthreshold", D["cmat"])],
            cats, colors, None)
    ax.set_title(f"{D['n_c']} misses · acuity agreement {D['agree']*100:.1f}%",
                 fontsize=FS_S, color=SUB, pad=2)

    # legend (shared), top-right
    for i, (c, lab) in enumerate(zip(colors, cats)):
        CV.add_patch(plt.Rectangle((124, 10 + i * 4.2), 2.4, 2.4, color=c, lw=0))
        CV.text(127.6, 11.2 + i * 4.2, lab, fontsize=FS_S, va="center")
    CV.text(124, 7.5, "Miss category", fontsize=FS_S, color=SUB, va="top", weight="bold")
    CV.text(124, 25, "Decoding: encoder\nrepresented the finding\n(classifier scored it)\n"
            "but the report was silent.", fontsize=FS_S, color=SUB, va="top", linespacing=1.3)

    # c — decoding misses by finding (primary)
    letter(0, 48, "c", "Decoding misses by critical finding")
    ax = ax_mm(44, 56, 30, 34)
    labs = [LBL[k] for k, _ in D["byf"]]; vals = [v for _, v in D["byf"]]
    yy = np.arange(len(labs))[::-1]
    ax.barh(yy, vals, color=CLS, height=0.64, lw=0, zorder=3)
    for y, v in zip(yy, vals):
        ax.text(v + 0.2, y, str(v), va="center", ha="left", fontsize=FS_S, color=INK)
    ax.set_yticks(yy); ax.set_yticklabels(labs, fontsize=FS_S)
    ax.set_xlim(0, max(vals) + 1.5); ax.set_xticks(range(0, max(vals) + 1, 2))
    ax.set_xlabel("Decoding misses (of 40)")

    # d — fraction of reports reading as normal
    letter(84, 48, "d", "Reports reading as normal")
    ax = ax_mm(98, 56, 28, 34)
    bars = [("Urgent", D["d_urg"], RPT), ("Non-urgent", D["d_nu"], PER)]
    for i, (lab, v, c) in enumerate(bars):
        ax.bar(i, v * 100, width=0.6, color=c, lw=0, zorder=3)
        ax.text(i, v * 100 + 2, f"{round(v*100)}%", ha="center", va="bottom", fontsize=FS_S,
                color=INK, weight="bold")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Urgent", "Non-urgent"])
    ax.set_ylim(0, 108); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Reading as normal (%)")

    # e — judge agreement (GPT-5 vs Claude; and judge vs rule-based detector)
    letter(140, 48, "e", "Judge agreement")
    ax = ax_mm(151, 56, 25, 34)
    vals = [("GPT-5 vs\nClaude", D["kappa"]), ("vs rule-\nbased (hem.)", D["krule"])]
    for i, (lab, v) in enumerate(vals):
        ax.bar(i, v, width=0.5, color=SUB, lw=0, zorder=3)
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=FS_S,
                color=INK, weight="bold")
    ax.axhline(0.8, color=RULE, lw=0.5, ls=(0, (2, 2)), zorder=1)
    ax.text(1.55, 0.8, "0.8", fontsize=FS_S, color=SUB, va="center", ha="left")
    ax.set_xticks([0, 1]); ax.set_xticklabels([v[0] for v in vals], fontsize=FS_S)
    ax.set_xlim(-0.6, 1.6)
    ax.set_ylim(0, 1.05); ax.set_yticks([0, 0.5, 1.0])
    ax.set_ylabel("Mean Cohen's κ")

    exts = ["png", "svg"] + (["pdf"] if a.pdf else [])
    for e in exts:
        fig.savefig(f"{a.out}.{e}", dpi=600 if e == "png" else None, facecolor="white")
    print("ED1 values:", json.dumps({k: (v if not isinstance(v, list) else dict(v))
          for k, v in D.items()}, default=str))
    print("saved", [f"{a.out}.{e}" for e in exts])


if __name__ == "__main__":
    main()
