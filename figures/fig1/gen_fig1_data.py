#!/usr/bin/env python
"""Generate the real inputs for make_fig1.py (GPT-5 primary):
  A2_sens_vs_flagrate.csv  (flag_rate, sensitivity) — head urgency score, screener-independent
  decoding_miss_scores.csv (score)                  — head score on the missed finding, 40 GPT decoding misses
  prints candidate IPH decoding-miss cases for the panel-a inset (study, score, prose)
"""
import json, csv
T="/project/hipaa_visishslab/neurovfm_triage_audit"; C=f"{T}/outputs/cache_path_a"; O=f"{T}/outputs/fig1_data"
import os; os.makedirs(O,exist_ok=True)
URG={"ich":["intracranial_hemorrhage"],"iph":["intraparenchymal_hemorrhage"],"ivh":["intraventricular_hemorrhage"],
"edh":["epidural_hematoma"],"sah":["aneurysmal_subarachnoid_hemorrhage","traumatic_subarachnoid_hemorrhage"],
"sdh":["acute_subdural_hematoma","subacute_chronic_subdural_hematoma"],
"calvarialfracture":["displaced_skull_fracture","nondisplaced_skull_fracture"],
"masseffect":["brain_mass_effect"],"midlineshift":["midline_shift"]}
P={json.loads(l)["study"]:json.loads(l)["probs"] for l in open(f"{C}/path_a_probs.jsonl") if l.strip()}
G={json.loads(l)["study"]:json.loads(l) for l in open(f"{T}/outputs/gpt_cq500/gpt.jsonl") if l.strip() and '"error"' not in l}
prose={json.loads(l)["study"]:json.loads(l).get("findings","") for l in open(f"{C}/path_b_triage.jsonl") if l.strip()}
def tru(v):
    try:return float(v)>=0.5
    except:return False
cons={};rd=csv.DictReader(open(f"{T}/data/cq500_consensus.csv"));idc=rd.fieldnames[0]
for r in rd: cons[r[idc].strip()]={f:tru(r.get(f,0)) for f in URG if f in r}
S=[s for s in P if s in cons and s in G]
def pa(s,f): return max(P[s].get(l,0) for l in URG[f])
def urg(s): return max(pa(s,f) for f in URG)
def gt(s): return any(cons[s].get(f) for f in URG)
nU=sum(gt(s) for s in S); n=len(S)
print(f"N={n} urgent={nU}")

# curve: head urgency score, sens vs flag rate (screener-independent)
ths=sorted({urg(s) for s in S},reverse=True)
with open(f"{O}/A2_sens_vs_flagrate.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["flag_rate","sensitivity"])
    w.writerow([0.0,0.0])
    for t in ths:
        fl=[s for s in S if urg(s)>=t]
        w.writerow([round(len(fl)/n,4), round(sum(gt(s) for s in fl)/nU,4)])

# 40 GPT-primary decoding misses + score on the missed finding
dec=[]
for s in S:
    if not gt(s) or G[s].get("acuity","").lower()=="urgent": continue
    pos=[f for f in URG if cons[s].get(f)]; r=max(pos,key=lambda f:pa(s,f)) if pos else None
    if r and not G[s].get("mentioned",{}).get(r,False) and pa(s,r)>0.5:
        dec.append((s,r,pa(s,r)))
with open(f"{O}/decoding_miss_scores.csv","w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["score"]); [w.writerow([round(sc,4)]) for _,_,sc in dec]
print(f"decoding misses: {len(dec)}; median score {sorted(sc for _,_,sc in dec)[len(dec)//2]:.3f}")

# candidate inset cases: IPH decoding misses with explicit false-normal prose
print("\n-- IPH decoding-miss inset candidates (study, score, prose[:70]) --")
for s,r,sc in sorted(dec,key=lambda x:-x[2]):
    if r=="iph":
        pr=" ".join(prose[s].split())
        print(f"   {s}  score={sc:.3f}  prose={pr[:70]!r}")
print(f"\nwrote -> {O}/")
