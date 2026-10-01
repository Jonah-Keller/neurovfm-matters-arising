#!/usr/bin/env python
"""Follow-up analyses for the auditor's reply. CQ500 cache only, no GPU.
B1 reconcile the 48-miss counts (finding-specific). B2 characterize the 34 empty reports.
B9 CQ500 calvarial-fracture AUROC. B8 prevalence. Normal-report rate urgent vs non-urgent.
"""
import json, csv, re, statistics
T="/project/hipaa_visishslab/neurovfm_triage_audit"; C=f"{T}/outputs/cache_path_a"
URG={"ich":["intracranial_hemorrhage"],"iph":["intraparenchymal_hemorrhage"],"ivh":["intraventricular_hemorrhage"],
"edh":["epidural_hematoma"],"sah":["aneurysmal_subarachnoid_hemorrhage","traumatic_subarachnoid_hemorrhage"],
"sdh":["acute_subdural_hematoma","subacute_chronic_subdural_hematoma"],
"calvarialfracture":["displaced_skull_fracture","nondisplaced_skull_fracture"],
"masseffect":["brain_mass_effect"],"midlineshift":["midline_shift"]}
def ld(p): return {json.loads(l)["study"]:json.loads(l) for l in open(p) if l.strip()}
probs=ld(f"{C}/path_a_probs.jsonl"); acu=ld(f"{C}/acuity_claude.jsonl"); hit=ld(f"{C}/prose_hit_claude.jsonl")
prose={json.loads(l)["study"]:json.loads(l).get("findings","") for l in open(f"{C}/path_b_triage.jsonl") if l.strip()}
def tru(v):
    try:return float(v)>=0.5
    except:return False
cons={}; rd=csv.DictReader(open(f"{T}/data/cq500_consensus.csv")); idc=rd.fieldnames[0]
for r in rd: cons[r[idc].strip()]={f:tru(r.get(f,0)) for f in URG if f in r}
S=[s for s in probs if s in cons and s in acu]
def pa(s,f): return max(probs[s]["probs"].get(l,0) for l in URG[f])
def gt_u(s): return any(cons[s].get(f) for f in URG)
def prose_u(s): return acu.get(s,{}).get("acuity","").lower()=="urgent"
TH=0.5
urg=[s for s in S if gt_u(s)]; missed=[s for s in urg if not prose_u(s)]
print(f"urgent={len(urg)} missed={len(missed)}  prevalence={len(urg)/len(S)*100:.0f}%")

# B1: reconcile counts
resp={}
for s in missed:
    pos=[f for f in URG if cons[s].get(f)]; resp[s]=max(pos,key=lambda f:pa(s,f)) if pos else None
any_label_high=sum(any(pa(s,f)>TH for f in URG) for s in missed)
specific_high=sum(pa(s,resp[s])>TH for s in missed if resp[s])
decoding=[s for s in missed if resp[s] and pa(s,resp[s])>TH and not hit.get(s,{}).get("mentioned",{}).get(resp[s],False)]
reasoning=[s for s in missed if resp[s] and hit.get(s,{}).get("mentioned",{}).get(resp[s],False)]
perception=[s for s in missed if resp[s] and pa(s,resp[s])<=TH and not hit.get(s,{}).get("mentioned",{}).get(resp[s],False)]
print(f"\n== B1 reconcile ==")
print(f"  ANY critical label > {TH}: {any_label_high}/48   (this was the '43/90%')")
print(f"  SPECIFIC missed finding > {TH}: {specific_high}/48   (stricter)")
print(f"  decoding (silent + specific high): {len(decoding)}/48 = {100*len(decoding)/len(missed):.0f}%")
print(f"  perception {len(perception)}  reasoning {len(reasoning)}  (sum {len(decoding)+len(perception)+len(reasoning)})")

# B2: characterize the decoding-miss reports
def norm_phrase(t):
    t=t.lower()
    return bool(re.search(r"no acute|unremarkable|within normal|no (significant )?abnormal|normal (study|ct|exam)|no evidence of acute|negative (study|for acute)",t))
lens_all=[len(prose[s]) for s in S if s in prose]
dec_texts=[(s,prose.get(s,"")) for s in decoding]
print(f"\n== B2 the {len(decoding)} decoding-miss reports ==")
empty=sum(1 for _,t in dec_texts if len(t.strip())<5)
normalish=sum(1 for _,t in dec_texts if norm_phrase(t))
print(f"  literally empty (<5 chars): {empty}")
print(f"  contain explicit normal/no-acute phrasing: {normalish}/{len(decoding)}")
print(f"  mean length: decoding={statistics.mean([len(t) for _,t in dec_texts]):.0f} chars vs all={statistics.mean(lens_all):.0f}")
print("  --- sample raw texts (first 3) ---")
for s,t in dec_texts[:3]:
    print(f"   [{s}] ({len(t)} ch): {re.sub(chr(10),' ',t)[:240]}")
# normal-report rate urgent vs non-urgent
def is_normal(s): return norm_phrase(prose.get(s,"")) or sum(hit.get(s,{}).get("mentioned",{}).values())==0
nu=[s for s in S if gt_u(s)]; nn=[s for s in S if not gt_u(s)]
print(f"\n  normal-reading report rate: urgent {sum(is_normal(s) for s in nu)}/{len(nu)} ({100*sum(is_normal(s) for s in nu)/len(nu):.0f}%)  "
      f"non-urgent {sum(is_normal(s) for s in nn)}/{len(nn)} ({100*sum(is_normal(s) for s in nn)/len(nn):.0f}%)")

# B9: CQ500 calvarial-fracture AUROC
def auroc(sc,y):
    pos=[a for a,b in zip(sc,y) if b]; neg=[a for a,b in zip(sc,y) if not b]
    if not pos or not neg: return None
    o=sorted(range(len(sc)),key=lambda i:sc[i]); rk=[0.]*len(sc); i=0
    while i<len(sc):
        j=i
        while j+1<len(sc) and sc[o[j+1]]==sc[o[i]]: j+=1
        for k in range(i,j+1): rk[o[k]]=(i+j)/2+1
        i=j+1
    return (sum(rk[i] for i in range(len(sc)) if y[i])-len(pos)*(len(pos)+1)/2)/(len(pos)*len(neg))
for f in ["calvarialfracture","ich","iph","sdh","sah","masseffect"]:
    a=auroc([pa(s,f) for s in S],[cons[s].get(f,False) for s in S])
    print(f"  CQ500 {f} AUROC: {a:.3f}" if a else f"  {f}: NA")
print("\n(B9 header line label:)  == CQ500 per-finding AUROC (fracture sanity) == above")
# save decoding texts for the reply
json.dump([{"study":s,"len":len(t),"normalish":norm_phrase(t),"text":t} for s,t in dec_texts],
          open(f"{T}/outputs/reviewer_suite/decoding_miss_reports.json","w"),indent=1)
print(f"\nwrote decoding_miss_reports.json ({len(dec_texts)} reports)")
