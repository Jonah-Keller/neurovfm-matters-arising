#!/usr/bin/env python
"""Recompute the headline numbers with the GPT-5 screener + GPT-5 mention judge as PRIMARY
(Claude = sensitivity analysis). CQ500 cache, no GPU. Deterministic (seeded bootstrap).
"""
import json, csv, random
random.seed(42)
T="/project/hipaa_visishslab/neurovfm_triage_audit"; C=f"{T}/outputs/cache_path_a"
URG={"ich":["intracranial_hemorrhage"],"iph":["intraparenchymal_hemorrhage"],"ivh":["intraventricular_hemorrhage"],
"edh":["epidural_hematoma"],"sah":["aneurysmal_subarachnoid_hemorrhage","traumatic_subarachnoid_hemorrhage"],
"sdh":["acute_subdural_hematoma","subacute_chronic_subdural_hematoma"],
"calvarialfracture":["displaced_skull_fracture","nondisplaced_skull_fracture"],
"masseffect":["brain_mass_effect"],"midlineshift":["midline_shift"]}
def ld(p): return {json.loads(l)["study"]:json.loads(l) for l in open(p) if l.strip()}
probs=ld(f"{C}/path_a_probs.jsonl")
gpt={json.loads(l)["study"]:json.loads(l) for l in open(f"{T}/outputs/gpt_cq500/gpt.jsonl") if l.strip() and '"error"' not in l}
prose={json.loads(l)["study"]:json.loads(l).get("findings","") for l in open(f"{C}/path_b_triage.jsonl") if l.strip()}
def tru(v):
    try:return float(v)>=0.5
    except:return False
cons={}; rd=csv.DictReader(open(f"{T}/data/cq500_consensus.csv")); idc=rd.fieldnames[0]
for r in rd: cons[r[idc].strip()]={f:tru(r.get(f,0)) for f in URG if f in r}
S=[s for s in probs if s in cons and s in gpt]     # single denominator
def pa(s,f): return max(probs[s]["probs"].get(l,0) for l in URG[f])
def urgsc(s): return max(pa(s,f) for f in URG)
def gt(s): return any(cons[s].get(f) for f in URG)
def scr(s): return gpt[s].get("acuity","").lower()=="urgent"      # GPT-5 screener
def ment(s,f): return bool(gpt[s].get("mentioned",{}).get(f,False)) # GPT-5 mention judge
TH=0.5
print(f"N (single denominator) = {len(S)}")
urg=[s for s in S if gt(s)]; missed=[s for s in urg if not scr(s)]
dec=[s for s in missed if (lambda r: r and not ment(s,r) and pa(s,r)>TH)(max([f for f in URG if cons[s].get(f)],key=lambda f:pa(s,f),default=None))]
perc=[];reas=[]
for s in missed:
    pos=[f for f in URG if cons[s].get(f)]; r=max(pos,key=lambda f:pa(s,f)) if pos else None
    if r and ment(s,r): reas.append(s)
    elif r and pa(s,r)>TH and not ment(s,r): pass
    elif r: perc.append(s)
print(f"\n== GPT-5 PRIMARY ==")
print(f"urgent={len(urg)}  missed={len(missed)}  decoding={len(dec)} ({100*len(dec)/len(missed):.0f}%)  perception={len(perc)}  reasoning={len(reas)}")
named_none=sum(sum(ment(s,f) for f in URG)==0 for s in dec)
print(f"decoding reports naming none of the nine reference findings: {named_none}/{len(dec)}")

def auroc(idx):
    pos=sum(1 for i in idx if gt(S[i])); neg=len(idx)-pos
    if not pos or not neg: return None
    av=sorted(((urgsc(S[i]),gt(S[i])) for i in idx),key=lambda x:x[0]); m=len(av); rk=[0.]*m; k=0
    while k<m:
        j=k
        while j+1<m and av[j+1][0]==av[k][0]: j+=1
        for t in range(k,j+1): rk[t]=(k+j)/2+1
        k=j+1
    return (sum(rk[t] for t in range(m) if av[t][1])-pos*(pos+1)/2)/(pos*neg)
def delta(idx):
    m=len(idx); g=[i for i in idx if gt(S[i])]
    if not g: return None
    pf=sum(scr(S[i]) for i in idx)/m; ps=sum(scr(S[i]) and gt(S[i]) for i in idx)/len(g)
    K=int(pf*m); top=sorted(idx,key=lambda i:-urgsc(S[i]))[:K]
    return sum(gt(S[i]) for i in top)/len(g)-ps
allidx=list(range(len(S)))
ps=sum(scr(s) and gt(s) for s in S)/len(urg); pf=sum(scr(s) for s in S)/len(S)
print(f"prose(GPT-5) point: sens={ps:.3f} @ flag_rate={pf:.3f}")
print(f"zero-param AUROC={auroc(allidx):.3f}  Δsens(matched)={delta(allidx):+.3f}")
A=[];D=[]
for _ in range(2000):
    bs=[random.randrange(len(S)) for _ in S]; a=auroc(bs); d=delta(bs)
    if a is not None:A.append(a)
    if d is not None:D.append(d)
def ci(x):x=sorted(x);return x[int(.025*len(x))],x[int(.975*len(x))]
al,ah=ci(A);dl,dh=ci(D)
print(f"bootstrap: AUROC 95%CI [{al:.3f},{ah:.3f}]  Δsens 95%CI [{dl:+.3f},{dh:+.3f}]")
# per-finding breakdown of GPT-5 decoding misses
from collections import Counter
dd=Counter()
for s in dec:
    pos=[f for f in URG if cons[s].get(f)]; dd[max(pos,key=lambda f:pa(s,f))]+=1
print("decoding-miss findings:",dict(dd.most_common()))
