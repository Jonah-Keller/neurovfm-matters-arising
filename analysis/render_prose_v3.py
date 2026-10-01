#!/usr/bin/env python
"""render_prose_v3 — the 'fuller' report. Same VALIDATED core as v2 (calibrated 11 findings -> parametric
prose, LLM-smoothed, guarded), PLUS an explicitly-separated 'AI-FLAGGED (uncalibrated)' section that
surfaces the other ~70 CT heads WITHOUT asserting them at the same confidence. Those heads have no CQ500
ground truth and over-fire cohort-wide (saturation audit), so we gate them the honest way: a label is
flagged only when THIS study is a cohort outlier for it (raw p>=0.9 AND >= p98 of that label's own
distribution across the cohort). Never prose, never asserted — a tagged watch-list for a human read.

  export ANTHROPIC_API_KEY=$(cat ~/.anthropic_key)
  python -m analysis.render_prose_v3 --studies CQ500-CT-181,CQ500-CT-427,CQ500-CT-99
Writes outputs/prose_v3.txt / .jsonl.
"""
import sys, json, argparse, re
from pathlib import Path
sys.path.insert(0, '.')
import numpy as np, pandas as pd
from analysis.render_prose_v2 import (logit, oof_platt, side_from_lat, NAME, LATERALIZABLE, load_jsonl,
                                      decide, deterministic_prose, guard_ok, SYS, CLAUDE_MODEL)
from src import config
import analysis.phase1_disagreement as p1

CACHE = Path("outputs/cache_path_a")
EXCLUDE = {"bleedlocation-left", "bleedlocation-right", "chronicbleed"}


def pretty(label):
    return label.replace("_", " ").strip().capitalize()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--studies", default="CQ500-CT-181,CQ500-CT-427,CQ500-CT-99")
    ap.add_argument("--pos", type=float, default=0.5); ap.add_argument("--neg", type=float, default=0.2)
    ap.add_argument("--out", default="outputs/prose_v3"); ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    import anthropic
    client = anthropic.Anthropic()

    cw = config.load_crosswalk()
    probs = load_jsonl(CACHE / "path_a_probs.jsonl")
    lat = load_jsonl(CACHE / "laterality_centroids.jsonl")
    acu = load_jsonl(CACHE / "acuity_claude.jsonl")
    cons = pd.read_csv("data/cq500_consensus.csv").set_index("name")
    studies = [s for s in sorted(probs) if s in cons.index]
    findings = [f for f in cw["findings"].keys() if f not in EXCLUDE]
    fraw = {f: np.array([p1.path_a_prob_on_finding(probs[s]["probs"], f, cw) or 0.0 for s in studies]) for f in findings}
    cal = {}
    for f in findings:
        if f in cons.columns:
            c = oof_platt(logit(fraw[f]), cons.loc[studies, f].astype(int).values)
            if c is not None:
                cal[f] = c
    idx = {s: i for i, s in enumerate(studies)}

    # uncalibrated CT heads = labels not mapped to any calibrated crosswalk finding
    mapped = {l for f in findings for l in config.candidate_labels_for(f, cw)}
    all_labels = list(next(iter(probs.values()))["probs"].keys())
    extra = [l for l in all_labels if l not in mapped]
    emat = {l: np.array([probs[s]["probs"].get(l, 0.0) for s in studies]) for l in extra}
    p98 = {l: float(np.percentile(emat[l], 98)) for l in extra}

    want = [s.strip() for s in a.studies.split(",") if s.strip() in idx]
    if a.studies.strip().lower() == "all":
        want = list(studies)
    done = set()
    outtxt, outjs = a.out + ".txt", a.out + ".jsonl"
    if a.resume and Path(outjs).exists():
        for l in open(outjs):
            if l.strip():
                done.add(json.loads(l)["study"])
        want = [s for s in want if s not in done]
    txt = open(outtxt, "a" if a.resume else "w"); js = open(outjs, "a" if a.resume else "w")
    for s in want:
        i = idx[s]
        cp = {f: (cal[f][i] if f in cal else fraw[f][i]) for f in findings}
        side = side_from_lat(lat.get(s, {}).get("lat")) if s in lat else None
        pos, neg, indet, imp = decide(cp, side, a.pos, a.neg)
        det_find, det_imp = deterministic_prose(pos, neg, indet, imp)
        asserted_terms = [NAME[f].split()[-1].lower() for f, _, _ in pos]
        find, impr, used = det_find, det_imp, "deterministic"
        facts = "STATEMENTS:\n" + "\n".join(f"- {t}" for _, t, _ in pos) + \
                ("\n- " + "\n- ".join(indet) if indet else "") + ("\n- " + "\n- ".join(neg) if neg else "")
        try:
            m = client.messages.create(model=CLAUDE_MODEL, max_tokens=500, system=SYS,
                                       messages=[{"role": "user", "content": facts}])
            out = m.content[0].text.strip()
            mf = re.search(r"FINDINGS:\s*(.+?)\s*IMPRESSION:\s*(.+)$", out, re.S | re.I)
            if mf and guard_ok(mf.group(1), out, asserted_terms):
                find, impr, used = mf.group(1).strip(), mf.group(2).strip(), "llm-smoothed"
            else:
                used = "deterministic (guard)"
        except Exception as e:
            used = f"deterministic (LLM err {repr(e)[:40]})"

        second = [(f, cp[f], side if f in LATERALIZABLE and side else None) for f, _, _ in pos]
        sr = "\n".join(f"  {NAME[f]}{', '+sd if sd else ''} — calibrated p={p:.2f}" for f, p, sd in second) or "  (none)"
        # uncalibrated cohort-outlier flags
        flags = [(l, probs[s]["probs"].get(l, 0.0)) for l in extra
                 if probs[s]["probs"].get(l, 0.0) >= 0.9 and probs[s]["probs"].get(l, 0.0) >= p98[l]]
        flags.sort(key=lambda t: -t[1])
        fl = "\n".join(f"  {pretty(l)} — raw p={p:.2f}" for l, p in flags[:8]) or "  (none)"
        acuity = (acu.get(s, {}) or {}).get("acuity", "n/a")
        block = (f"{'='*78}\nSTUDY {s}   |   CT head, non-contrast   |   realization: {used}\n{'='*78}\n"
                 f"FINDINGS: {find}\nIMPRESSION: {impr}\nACUITY (model triage): {acuity}\n\n"
                 f"--- VALIDATED FINDINGS (calibrated dx head, out-of-fold) ---\n{sr}\n\n"
                 f"--- AI-FLAGGED (UNCALIBRATED — not asserted; cohort-outlier only, review) ---\n{fl}\n")
        txt.write(block + "\n"); txt.flush()
        js.write(json.dumps({"study": s, "realization": used, "findings": find, "impression": impr,
                 "validated": [{"finding": f, "cal_p": float(p), "side": sd} for f, p, sd in second],
                 "flagged_uncalibrated": [{"label": l, "raw_p": float(p)} for l, p in flags]}) + "\n")
        js.flush()
        if len(want) <= 6:
            print(block, flush=True)
    txt.close(); js.close()
    print(f"-> {outtxt} / {outjs}")


if __name__ == "__main__":
    main()
