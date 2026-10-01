#!/usr/bin/env python
"""Reviewer analysis suite — runs the cheap, cache-only analyses requested in review.
All on CQ500 cached outputs (public data). No GPU.

A0 study counts (Q1)        A1 perception/decoding/reasoning decomposition (Fig 1b)
A2 zero-parameter urgency score vs prose point (the missing baseline)
A3 critical-list coverage   A4 secondary-finding stratification
A5 calibration / reliability (CQ500)
"""
import json, csv, glob, math, os
T = "/project/hipaa_visishslab/neurovfm_triage_audit"
C = f"{T}/outputs/cache_path_a"
OUT = f"{T}/outputs/reviewer_suite"; os.makedirs(OUT, exist_ok=True)

# urgent CQ500 findings -> NeuroVFM labels (from mapping/cq500_to_neurovfm_ct.yaml)
URGENT = {
    "ich": ["intracranial_hemorrhage"],
    "iph": ["intraparenchymal_hemorrhage"],
    "ivh": ["intraventricular_hemorrhage"],
    "edh": ["epidural_hematoma"],
    "sah": ["aneurysmal_subarachnoid_hemorrhage", "traumatic_subarachnoid_hemorrhage"],
    "sdh": ["acute_subdural_hematoma", "subacute_chronic_subdural_hematoma"],
    "calvarialfracture": ["displaced_skull_fracture", "nondisplaced_skull_fracture"],
    "masseffect": ["brain_mass_effect"],
    "midlineshift": ["midline_shift"],
}
THR = 0.5  # diagnostic-head operating threshold

def load_jsonl(p):
    out = {}
    for line in open(p):
        line = line.strip()
        if not line: continue
        r = json.loads(line); out[r["study"]] = r
    return out

probs = load_jsonl(f"{C}/path_a_probs.jsonl")           # study -> {probs:{label:p}}
hit   = load_jsonl(f"{C}/prose_hit_claude.jsonl")         # study -> {mentioned:{finding:bool}}
acu   = load_jsonl(f"{C}/acuity_claude.jsonl")            # study -> {acuity:str}

# consensus ground truth
def truthy(v):
    try: return float(v) >= 0.5
    except Exception: return str(v).strip().lower() in ("true", "yes", "pos")
cons = {}
rdr = csv.DictReader(open(f"{T}/data/cq500_consensus.csv"))
idcol = rdr.fieldnames[0]
for row in rdr:
    name = row[idcol].strip()
    cons[name] = {f: truthy(row.get(f, 0)) for f in URGENT if f in row}

# normalize study-id join
def match(sid, keyset):
    if sid in keyset: return sid
    for cand in (sid.replace("CQ500-CT-", ""), f"CQ500-CT-{sid}",
                 sid.replace("CQ500-CT-", "CQ500-CT-0"), sid.lstrip("0")):
        if cand in keyset: return cand
    return None

studies = [s for s in probs if match(s, cons)]
def pa_score(s, finding):
    p = probs[s]["probs"]; return max((p.get(l, 0.0) for l in URGENT[finding]), default=0.0)
def pa_urgency(s):            # zero-parameter triage score
    return max(pa_score(s, f) for f in URGENT)
def gt_urgent(s):
    c = cons[match(s, cons)]; return any(c.get(f, False) for f in URGENT)
def prose_urgent(s):
    return acu.get(s, {}).get("acuity", "").lower() == "urgent"

print(f"joined CQ500 studies: {len(studies)} (probs {len(probs)}, consensus {len(cons)}, acuity {len(acu)}, hit {len(hit)})")

# ---------- A0: study counts (Q1) ----------
urgent_studies = [s for s in studies if gt_urgent(s)]
missed = [s for s in urgent_studies if not prose_urgent(s)]          # prose pipeline missed
missed_pa_high = [s for s in missed if pa_urgency(s) > THR]
print("\n== A0 study counts (Q1) ==")
print(f"  urgent studies (GT)           : {len(urgent_studies)}")
print(f"  missed by prose triage        : {len(missed)}  ({100*len(missed)/max(1,len(urgent_studies)):.1f}% of urgent)")
print(f"  of misses, Path-A > {THR}       : {len(missed_pa_high)}  ({100*len(missed_pa_high)/max(1,len(missed)):.1f}% of misses)")

# ---------- A1: perception / decoding / reasoning decomposition (Fig 1b) ----------
cat = {"perception": 0, "decoding": 0, "reasoning": 0}
rows = []
for s in missed:
    c = cons[match(s, cons)]
    pos_findings = [f for f in URGENT if c.get(f, False)]
    # pick the responsible finding = highest Path-A among GT-positive urgent findings
    resp = max(pos_findings, key=lambda f: pa_score(s, f)) if pos_findings else None
    mentioned = hit.get(s, {}).get("mentioned", {}).get(resp, False) if resp else False
    pahigh = pa_score(s, resp) > THR if resp else False
    if mentioned:
        k = "reasoning"           # prose named it, screener didn't escalate
    elif pahigh:
        k = "decoding"            # encoder saw it, prose dropped it
    else:
        k = "perception"          # encoder didn't see it either
    cat[k] += 1
    rows.append({"study": s, "finding": resp, "pa": round(pa_score(s, resp), 3) if resp else "",
                 "mentioned": mentioned, "category": k})
print("\n== A1 decomposition of prose misses (Fig 1b) ==")
for k, v in cat.items():
    print(f"  {k:<11}: {v}  ({100*v/max(1,len(missed)):.0f}%)")
csv.DictWriter(open(f"{OUT}/A1_decomposition.csv", "w", newline=""),
               fieldnames=["study", "finding", "pa", "mentioned", "category"]).writerows(rows) if False else None
with open(f"{OUT}/A1_decomposition.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["study", "finding", "pa", "mentioned", "category"]); w.writeheader(); w.writerows(rows)

# ---------- A2: zero-parameter urgency score vs prose point ----------
def auroc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y]; neg = [s for s, y in zip(scores, labels) if not y]
    if not pos or not neg: return None
    order = sorted(range(len(scores)), key=lambda i: scores[i]); ranks = [0.0]*len(scores); i = 0
    while i < len(scores):
        j = i
        while j+1 < len(scores) and scores[order[j+1]] == scores[order[i]]: j += 1
        r = (i+j)/2.0 + 1.0
        for k in range(i, j+1): ranks[order[k]] = r
        i = j+1
    sp = sum(ranks[i] for i in range(len(scores)) if labels[i])
    return (sp - len(pos)*(len(pos)+1)/2.0)/(len(pos)*len(neg))
sc = [pa_urgency(s) for s in studies]; yy = [gt_urgent(s) for s in studies]
roc_auc = auroc(sc, yy)
# prose operating point
n_all = len(studies)
prose_flag = sum(prose_urgent(s) for s in studies)
prose_tp = sum(prose_urgent(s) and gt_urgent(s) for s in studies)
prose_sens = prose_tp/max(1, len(urgent_studies)); prose_flagrate = prose_flag/n_all
# zero-param sensitivity at the SAME flag rate
thr_grid = sorted(set(sc), reverse=True)
def sens_at_flagrate(target):
    best = 0.0
    for t in thr_grid:
        flagged = [s for s in studies if pa_urgency(s) >= t]
        fr = len(flagged)/n_all
        if fr <= target + 1e-9:
            sens = sum(gt_urgent(s) for s in flagged)/max(1, len(urgent_studies)); best = sens
        else: break
    return best
zp_sens_matched = sens_at_flagrate(prose_flagrate)
print("\n== A2 zero-parameter urgency score (missing baseline) ==")
print(f"  urgency-score AUROC (urgent study)   : {roc_auc:.3f}" if roc_auc else "  AUROC: NA")
print(f"  PROSE pipeline point: sens={prose_sens:.3f} @ flag_rate={prose_flagrate:.3f}")
print(f"  ZERO-PARAM at matched flag_rate      : sens={zp_sens_matched:.3f}  (Δ={zp_sens_matched-prose_sens:+.3f})")
# dump the curve
with open(f"{OUT}/A2_sens_vs_flagrate.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["threshold", "flag_rate", "sensitivity"])
    for t in thr_grid:
        fl = [s for s in studies if pa_urgency(s) >= t]
        w.writerow([round(t, 4), round(len(fl)/n_all, 4), round(sum(gt_urgent(s) for s in fl)/max(1, len(urgent_studies)), 4)])

# ---------- A3: critical-list coverage ----------
covered = sum(1 for f in URGENT if URGENT[f])
print("\n== A3 critical-list coverage ==")
print(f"  CQ500 urgent findings mapped to >=1 NeuroVFM label: {covered}/{len(URGENT)}")
print("  (ASNR ref-17 full list mapping: pending the enumerated reference)")

# ---------- A4: secondary-finding stratification ----------
dec = [r["study"] for r in rows if r["category"] == "decoding"]
# correctly-reported urgent: GT urgent, prose mentioned the responsible finding
correct = []
for s in urgent_studies:
    c = cons[match(s, cons)]; pos = [f for f in URGENT if c.get(f, False)]
    resp = max(pos, key=lambda f: pa_score(s, f)) if pos else None
    if resp and hit.get(s, {}).get("mentioned", {}).get(resp, False): correct.append((s, resp))
def n_other_mentions(s, target):
    m = hit.get(s, {}).get("mentioned", {}); return sum(1 for k, v in m.items() if v and k != target)
dec_other = [n_other_mentions(s, next(r["finding"] for r in rows if r["study"] == s)) for s in dec]
cor_other = [n_other_mentions(s, t) for s, t in correct]
def mean(x): return sum(x)/len(x) if x else float("nan")
print("\n== A4 secondary-finding stratification ==")
print(f"  decoding misses (n={len(dec_other)}): mean other findings named = {mean(dec_other):.2f}")
print(f"  correctly reported (n={len(cor_other)}): mean other findings named = {mean(cor_other):.2f}")

# ---------- A5: calibration (CQ500) ----------
pairs = []  # (pred_prob, gt) pooled over urgent findings
for s in studies:
    c = cons[match(s, cons)]
    for f in URGENT:
        pairs.append((pa_score(s, f), 1 if c.get(f, False) else 0))
bins = [0]*10; bsum = [0.0]*10; bpos = [0]*10
for p, y in pairs:
    b = min(9, int(p*10)); bins[b] += 1; bsum[b] += p; bpos[b] += y
ece = sum(bins[b]/len(pairs)*abs(bsum[b]/bins[b]-bpos[b]/bins[b]) for b in range(10) if bins[b])
print("\n== A5 calibration (CQ500, pooled urgent findings) ==")
print(f"  ECE = {ece:.3f}  (n pairs={len(pairs)})")
with open(f"{OUT}/A5_reliability_cq500.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["bin", "n", "mean_pred", "obs_freq"])
    for b in range(10):
        if bins[b]: w.writerow([f"{b/10:.1f}-{(b+1)/10:.1f}", bins[b], round(bsum[b]/bins[b], 3), round(bpos[b]/bins[b], 3)])

json.dump({"A0": {"urgent": len(urgent_studies), "missed": len(missed), "missed_pa_high": len(missed_pa_high)},
           "A1": cat, "A2": {"auroc": roc_auc, "prose_sens": prose_sens, "prose_flagrate": prose_flagrate,
                             "zp_sens_matched": zp_sens_matched, "delta": zp_sens_matched-prose_sens},
           "A3": {"covered": covered, "total": len(URGENT)},
           "A4": {"decoding_mean_other": mean(dec_other), "correct_mean_other": mean(cor_other)},
           "A5": {"ece": ece}}, open(f"{OUT}/summary.json", "w"), indent=1)
print(f"\nwrote -> {OUT}/")
