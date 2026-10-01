#!/usr/bin/env python
"""Contact-sheet of all axial slices (brain window) with slice-index labels, so a
reader can pick the slice that best shows the finding. Usage:
  render_montage.py <CQ500-CT-NNN> <out.png>
Then render the chosen slice with render_inset.py --slice <k>.
"""
import sys, os, glob
sys.path.insert(0, "data")
import numpy as np, pydicom, cq500_index
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

name, out = sys.argv[1], sys.argv[2]
d = cq500_index.resolve_study_dir(name)
best = max(cq500_index.series_dirs(d), key=lambda s: len(glob.glob(os.path.join(s, "*.dcm"))))
sl = []
for f in glob.glob(os.path.join(best, "*.dcm")):
    try:
        ds = pydicom.dcmread(f); z = float(ds.ImagePositionPatient[2])
        a = ds.pixel_array.astype(np.float32) * float(getattr(ds, "RescaleSlope", 1)) + float(getattr(ds, "RescaleIntercept", 0))
        sl.append((z, a))
    except Exception: pass
sl.sort(key=lambda t: t[0]); vol = np.stack([a for _, a in sl])
Z = len(vol); cols = 6; rows = int(np.ceil(Z / cols))
fig, axes = plt.subplots(rows, cols, figsize=(cols * 1.8, rows * 1.8))
for i, ax in enumerate(axes.ravel()):
    ax.axis("off")
    if i < Z:
        ax.imshow(np.clip((vol[i] - 0) / 80, 0, 1), cmap="gray")   # brain window L40/W80
        ax.text(0.04, 0.96, str(i), transform=ax.transAxes, color="yellow", fontsize=9,
                va="top", ha="left", weight="bold")
fig.suptitle(f"{name} — pick the slice index with the clearest finding", fontsize=11)
plt.tight_layout(); plt.savefig(out, dpi=130, facecolor="white"); print(f"wrote {out} ({Z} slices)")
