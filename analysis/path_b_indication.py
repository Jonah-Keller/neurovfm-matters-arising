#!/usr/bin/env python
"""Indication ablation: rerun NeuroVFM Path-B (findings LLM) on CQ500 WITH a clinical
indication (vs the cache's clinical_context=""). Same images, same series pooling as the
original cache. One array element processes a chunk. Resumable.

Usage: path_b_indication.py <indication> <worklist.txt> <out.jsonl>
"""
import sys, os, json
sys.path.insert(0, "src"); sys.path.insert(0, "data")
import cq500_index
from build_cache import _load_study_resilient
import wrappers

IND, WL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
# resolve MIG slice
if not os.environ.get("CUDA_VISIBLE_DEVICES"):
    for k, v in os.environ.items():
        if k.startswith("CUDA_VISIBLE_DEVICES") and k != "CUDA_VISIBLE_DEVICES" and v:
            os.environ["CUDA_VISIBLE_DEVICES"] = v; break
import torch
assert torch.cuda.is_available(), "no GPU"
print(f"GPU {torch.cuda.get_device_name(0)}; indication={IND!r}", flush=True)

names = [l.strip() for l in open(WL) if l.strip()]
done = set()
if os.path.exists(OUT):
    done = {json.loads(l)["study"] for l in open(OUT) if l.strip()}
todo = [n for n in names if n not in done]
print(f"{len(names)} studies, {len(todo)} to do", flush=True)
if not todo: sys.exit(0)

encoder, preprocessor, dx_head, generator, gen_preproc = wrappers.load_models(device="cuda", load_vlm=True)
print("models loaded", flush=True)
import time; t0 = time.time(); n = 0
with open(OUT, "a") as fh:
    for name in todo:
        try:
            d = cq500_index.resolve_study_dir(name)
            if not d:
                fh.write(json.dumps({"study": name, "error": "unresolved"}) + "\n"); fh.flush(); continue
            batch = _load_study_resilient(gen_preproc, cq500_index.series_dirs(d))
            findings = wrappers.run_path_b(generator, batch, clinical_context=IND)
            fh.write(json.dumps({"study": name, "findings": findings}) + "\n"); fh.flush()
        except Exception as e:
            fh.write(json.dumps({"study": name, "error": str(e)[:200]}) + "\n"); fh.flush()
        n += 1
        if n % 10 == 0: print(f"  {n}/{len(todo)} ({time.time()-t0:.0f}s)", flush=True)
print(f"done {n} -> {OUT}", flush=True)
