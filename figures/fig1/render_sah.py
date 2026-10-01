#!/usr/bin/env python
"""SAH inset: auto-locate the basal-cistern hyperdensity, render the best slice as the
inset PNG, and a focused labeled montage (peak +/- band) for confirmation / re-pick.
Usage: render_sah.py <CQ500-CT-NNN> <out_inset.png> <out_montage.png> [slice_override]
"""
import sys, os, glob
sys.path.insert(0, "data")
import numpy as np, pydicom, cq500_index
from scipy import ndimage
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

name, out_inset, out_mont = sys.argv[1], sys.argv[2], sys.argv[3]
override = int(sys.argv[4]) if len(sys.argv) > 4 else None
d = cq500_index.resolve_study_dir(name)
best = max(cq500_index.series_dirs(d), key=lambda s: len(glob.glob(os.path.join(s, "*.dcm"))))
sl = []
for f in glob.glob(os.path.join(best, "*.dcm")):
    try:
        ds = pydicom.dcmread(f); z = float(ds.ImagePositionPatient[2])
        a = ds.pixel_array.astype(np.float32) * float(getattr(ds, "RescaleSlope", 1)) + float(getattr(ds, "RescaleIntercept", 0))
        sl.append((z, a))
    except Exception: pass
sl.sort(key=lambda t: t[0]); vol = np.stack([a for _, a in sl]); Z, H, Wd = vol.shape

# SAH = hyperdense CSF in basal cisterns: central region, lower-middle band
cy, cx = H // 2, Wd // 2
yy, xx = np.ogrid[:H, :Wd]
central = ((yy - cy) / (0.30 * H)) ** 2 + ((xx - cx) / (0.30 * Wd)) ** 2 <= 1  # tight centre (cisterns)
score = np.zeros(Z)
for z in range(Z):
    s = vol[z]
    brain = ndimage.binary_erosion((s > -10) & (s < 100), iterations=4)
    score[z] = int(((s >= 45) & (s <= 95) & central & brain).sum())
band = np.zeros(Z, bool); band[int(0.28 * Z):int(0.62 * Z)] = True   # basal-cistern band
score = np.where(band, score, 0)
k = override if override is not None else int(np.argmax(score))
print(f"{name}: {Z} slices, SAH slice idx={k} (score={int(score[k])})")

def win(s):  # brain window L40/W80
    return np.clip((s - 0) / 80, 0, 1)

# inset (cropped to head)
img = win(vol[k]); m = vol[k] > -200
ys, xs = np.where(m); img = img[ys.min():ys.max()+1, xs.min():xs.max()+1]
plt.imsave(out_inset, img, cmap="gray", dpi=600)

# focused montage: k +/- 7 (every slice), labelled
idxs = [i for i in range(k - 7, k + 8) if 0 <= i < Z]
cols = 5; rows = int(np.ceil(len(idxs) / cols))
fig, axes = plt.subplots(rows, cols, figsize=(cols * 1.8, rows * 1.8))
for ax, i in zip(axes.ravel(), idxs + [None] * (rows * cols - len(idxs))):
    ax.axis("off")
    if i is not None:
        ax.imshow(win(vol[i]), cmap="gray")
        ax.text(0.05, 0.95, str(i), transform=ax.transAxes, color="yellow", fontsize=11,
                va="top", weight="bold")
        if i == k: ax.set_title("auto-pick", fontsize=8, color="#c04000")
fig.suptitle(f"{name} SAH — slices around the basal cisterns (pick an index)", fontsize=10)
plt.tight_layout(); plt.savefig(out_mont, dpi=140, facecolor="white")
print(f"wrote {out_inset} and {out_mont}")
