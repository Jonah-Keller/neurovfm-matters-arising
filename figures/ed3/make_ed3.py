"""Extended Data Fig. 3 — six representative decoding misses. 2x3 montage: each cell shows a
key axial slice (brain window; bone window for calvarial fracture), the classifier's nine
critical-finding scores (responsible finding highlighted), and the generated report verbatim.
Usage: python make_ed3.py --out ed3
"""
import argparse, json, glob, os, sys, textwrap
import numpy as np
import pydicom
from scipy import ndimage
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

T = "/project/hipaa_visishslab/neurovfm_triage_audit"
sys.path.insert(0, f"{T}/data")
import cq500_index
C = f"{T}/outputs/cache_path_a"
URG = {"ich": ["intracranial_hemorrhage"], "iph": ["intraparenchymal_hemorrhage"],
       "ivh": ["intraventricular_hemorrhage"], "edh": ["epidural_hematoma"],
       "sah": ["aneurysmal_subarachnoid_hemorrhage", "traumatic_subarachnoid_hemorrhage"],
       "sdh": ["acute_subdural_hematoma", "subacute_chronic_subdural_hematoma"],
       "calvarialfracture": ["displaced_skull_fracture", "nondisplaced_skull_fracture"],
       "masseffect": ["brain_mass_effect"], "midlineshift": ["midline_shift"]}
ORDER = ["ich", "iph", "ivh", "edh", "sah", "sdh", "calvarialfracture", "masseffect", "midlineshift"]
SHORT = {"ich": "ICH", "iph": "IPH", "ivh": "IVH", "edh": "EDH", "sah": "SAH", "sdh": "SDH",
         "calvarialfracture": "Fx", "masseffect": "Mass", "midlineshift": "MLS"}
LBL = {"sah": "Subarachnoid hemorrhage", "iph": "Intraparenchymal hemorrhage",
       "sdh": "Subdural hematoma", "ich": "Intracranial hemorrhage",
       "calvarialfracture": "Calvarial fracture", "masseffect": "Mass effect"}
CLS, RPT, INK, SUB = "#0072B2", "#D55E00", "#1a1a1a", "#5c5c5c"


def ld(p): return {json.loads(l)["study"]: json.loads(l) for l in open(p) if l.strip()}


def load_vol(name):
    d = cq500_index.resolve_study_dir(name)
    best = max(cq500_index.series_dirs(d), key=lambda s: len(glob.glob(os.path.join(s, "*.dcm"))))
    sl = []
    for f in glob.glob(os.path.join(best, "*.dcm")):
        try:
            ds = pydicom.dcmread(f); z = float(ds.ImagePositionPatient[2])
            a = ds.pixel_array.astype(np.float32) * float(getattr(ds, "RescaleSlope", 1)) + float(getattr(ds, "RescaleIntercept", 0))
            sl.append((z, a))
        except Exception: pass
    sl.sort(key=lambda t: t[0])
    return np.stack([a for _, a in sl])


def pick_slice(vol, finding):
    Z, H, Wd = vol.shape
    if finding == "calvarialfracture":
        return int(0.58 * Z)                       # upper skull, bone window
    if finding == "masseffect":
        return int(0.5 * Z)                        # central
    # hemorrhages: slice with most acute-blood voxels (50-90 HU) inside the head
    score = np.zeros(Z)
    for z in range(Z):
        s = vol[z]; head = (s > -200) & (s < 300)
        head = ndimage.binary_erosion(head, iterations=2)
        score[z] = int(((s >= 50) & (s <= 90) & head).sum())
    band = np.zeros(Z, bool); band[int(0.2 * Z):int(0.8 * Z)] = True
    score = np.where(band, score, 0)
    return int(np.argmax(score))


def win(s, finding):
    if finding == "calvarialfracture":
        return np.clip((s - (600 - 1400)) / 2800, 0, 1)   # bone WL600 WW2800
    return np.clip((s - 0) / 80, 0, 1)                     # brain WL40 WW80


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default="ed3")
    ap.add_argument("--pdf", action="store_true"); a = ap.parse_args()
    cases = json.load(open(f"{T}/outputs/fig1_data/ed3_cases.json"))
    P = {s: r["probs"] for s, r in ld(f"{C}/path_a_probs.jsonl").items()}
    RP = {s: r.get("findings", "") for s, r in ld(f"{C}/path_b_triage.jsonl").items()}
    pa = lambda s, f: max(P[s].get(l, 0) for l in URG[f])

    order = ["sah", "iph", "sdh", "ich", "calvarialfracture", "masseffect"]
    plt.rcParams.update({"font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "Liberation Sans", "DejaVu Sans"], "svg.fonttype": "none"})
    fig, axes = plt.subplots(2, 3, figsize=(183 / 25.4, 142 / 25.4))
    for ax, f in zip(axes.ravel(), order):
        name = cases[f]
        vol = load_vol(name); k = pick_slice(vol, f)
        img = win(vol[k], f); m = vol[k] > -200
        ys, xs = np.where(m)
        if len(ys): img = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        ax.imshow(img, cmap="gray", interpolation="lanczos"); ax.axis("off")
        ax.set_title(f"{LBL[f]} — classifier {pa(name, f):.2f}", fontsize=6.5, color=CLS,
                     weight="bold", pad=2)
        # report snippet (verbatim, trimmed + wrapped to the panel width)
        rep = RP[name].split("Findings:")[-1].strip().replace("\n", " ")
        rep = (rep[:78].rstrip() + "…") if len(rep) > 78 else rep
        rep = "\n".join(textwrap.wrap(rep, 46)[:2])
        ax.text(0.5, -0.05, f"Report: “{rep}”", transform=ax.transAxes, ha="center", va="top",
                fontsize=5.0, color=RPT)
        # mini score bar (9 findings), highlight responsible
        iax = ax.inset_axes([0.07, -0.50, 0.86, 0.13])
        vals = [pa(name, ff) for ff in ORDER]
        cols = [RPT if ff == f else "#b9c6d6" for ff in ORDER]
        iax.bar(range(9), vals, color=cols, lw=0, width=0.8)
        iax.axhline(0.5, color="#aaa", lw=0.4, ls=(0, (2, 2)))
        iax.set_ylim(0, 1); iax.set_xticks(range(9))
        iax.set_xticklabels([SHORT[ff] for ff in ORDER], fontsize=4.4, rotation=90)
        iax.set_yticks([0, 1]); iax.tick_params(length=1.5, labelsize=4.4)
        for sp in ("top", "right"): iax.spines[sp].set_visible(False)
        print(f"rendered {f} {name} slice {k}/{vol.shape[0]}", flush=True)
    fig.suptitle("Representative decoding misses: classifier detected the finding, report read normal",
                 fontsize=7, y=0.99)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.20, wspace=0.08, hspace=1.15)
    exts = ["png", "svg"] + (["pdf"] if a.pdf else [])
    for e in exts:
        fig.savefig(f"{a.out}.{e}", dpi=600 if e == "png" else None, facecolor="white")
    print("saved", [f"{a.out}.{e}" for e in exts])


if __name__ == "__main__":
    main()
