#!/usr/bin/env python
"""Render the panel-a inset slice for the Fig.1 case (CQ500, public).
Auto-selects the axial slice with the most hyperdense parenchymal voxels (acute IPH
is hyperdense ~50-90 HU), brain-windows (L40/W80), crops to head, saves PNG.
Usage: render_inset.py <CQ500-CT-NNN> <out.png>
"""
import sys, os, glob
sys.path.insert(0, "data")
import numpy as np, pydicom
import cq500_index

name, out = sys.argv[1], sys.argv[2]
d = cq500_index.resolve_study_dir(name)
series = cq500_index.series_dirs(d)
# pick the axial series with the most slices
best = max(series, key=lambda s: len(glob.glob(os.path.join(s, "*.dcm"))))
files = glob.glob(os.path.join(best, "*.dcm"))
slices = []
for f in files:
    try:
        ds = pydicom.dcmread(f)
        z = float(ds.ImagePositionPatient[2])
        arr = ds.pixel_array.astype(np.float32)
        arr = arr * float(getattr(ds, "RescaleSlope", 1)) + float(getattr(ds, "RescaleIntercept", 0))
        slices.append((z, arr))
    except Exception:
        pass
slices.sort(key=lambda t: t[0])
vol = np.stack([a for _, a in slices])          # [Z, H, W] in HU
Z, H, Wd = vol.shape
from scipy import ndimage
# per-slice brain parenchyma mask = soft tissue/blood (HU -10..100), eroded to drop bone-adjacent voxels
hyper = np.zeros(Z)
for z in range(Z):
    sl = vol[z]
    brain = (sl > -10) & (sl < 100)
    brain = ndimage.binary_erosion(brain, iterations=6)   # pull away from skull
    # keep only the largest connected component (the brain), not scattered bone edges
    lab, n = ndimage.label(brain)
    if n:
        big = (lab == (1 + np.argmax(ndimage.sum(np.ones_like(lab), lab, range(1, n + 1)))))
        brain = big
    hyper[z] = int(((sl >= 50) & (sl <= 90) & brain).sum())
# restrict to the supratentorial band (avoid skull base and vertex)
band = np.zeros(Z, bool); band[int(0.45 * Z):int(0.95 * Z)] = True
hyper = np.where(band, hyper, 0)
k = int(np.argmax(hyper))
print(f"{name}: {Z} slices, hemorrhage slice idx={k} (hyperdense vox={int(hyper[k])})")
sl = vol[k]
# brain window L40 W80
lo, hi = 40 - 40, 40 + 40
img = np.clip((sl - lo) / (hi - lo), 0, 1)
# crop to head bounding box (tissue > ~ -200 HU)
mask = sl > -200
ys, xs = np.where(mask)
if len(ys):
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    img = img[y0:y1 + 1, x0:x1 + 1]
import matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
plt.imsave(out, img, cmap="gray", dpi=600)
print(f"wrote {out}  ({img.shape})")
