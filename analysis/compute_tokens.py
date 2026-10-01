#!/usr/bin/env python
"""Compute the matched-threshold tokens for the manuscript (GPT-5 primary; Claude sensitivity).
Matched threshold = classifier flags the same fraction (34.1%) of all 472 studies as the report
pipeline. Primary decomposition uses that threshold + 'report named none of the study's positive
critical findings'. Prints a token->value map.
"""
import json, csv, random
random.seed(42)
T="/project/hipaa_visishslab/neurovfm_triage_audit"; C=f"{T}/outputs/cache_path_a"
URG={"ich":["intracranial_hemorrhage"],"iph":["intraparenchymal_hemorrhage"],"ivh":["intraventricular_hemorrhage"],
"edh":["epidural_hematoma"],"sah":["aneurysmal_subarachnoid_hemorrhage","traumatic_subarachnoid_hemorrhage"],
"sdh":["acute_subdural_hematoma","subacute_chronic_subdural_hematoma"],
"calvarialfracture":["displaced_skull_fracture","nondisplaced_skull_fracture"],
"masseffect":["brain_mass_effect"],"midlineshift":["midline_shift"]}
FIND=list(URG)
def ld(p): return {json.loads(l)["study"]:json.loads(l) for l in open(p) if l.strip()}
P={s:r["probs"] for s,r in ld(f"{C}/path_a_probs.jsonl").items()}
G=ld(f"{T}/outputs/gpt_cq500/gpt.jsonl")
CA={s:r["acuity"].lower() for s,r in ld(f"{C}/acuity_claude.jsonl").items()}
CM={s:r["mentioned"] for s,r in ld(f"{C}/prose_hit_claude.jsonl").items()}
def tru(v):
    try:return float(v)>=0.5
    except:return False
cons={};rd=csv.DictReader(open(f"{T}/data/cq500_consensus.csv"));idc=rd.fieldnames[0]
for r in rd: cons[r[idc].strip()]={f:tru(r.get(f,0)) for f in URG if f in r}
S=[s for s in P if s in cons and s in G and '"error"' not in json.dumps(G[s])]
def pa(s,f): return max(P[s].get(l,0) for l in URG[f])
def urgsc(s): return max(pa(s,f) for f in URG)
def gt(s): return any(cons[s].get(f) for f in URG)
def posf(s): return [f for f in URG if cons[s].get(f)]
n=len(S); U=[s for s in S if gt(s)]; nU=len(U)

# matched threshold: flag 34.1% of all studies
scores=sorted((urgsc(s) for s in S),reverse=True)
k=round(0.341*n); THR=scores[k-1]
flagged=[s for s in S if urgsc(s)>=THR]
print(f"N={n} urgent={nU} matched_flag={len(flagged)} ({len(flagged)/n:.3f}) THR={THR:.4f}")

def gpt_urgent(s): return G[s].get("acuity","").lower()=="urgent"
def gpt_ment_any_pos(s): m=G[s].get("mentioned",{}); return any(m.get(f) for f in posf(s))
def cls_detect(s): return urgsc(s)>=THR

# 2x2 on urgent studies
both=cls=rep=neither=0
for s in U:
    c=cls_detect(s); r=gpt_urgent(s)
    both+=c and r; cls+=c and not r; rep+=r and not c; neither+=not c and not r
print(f"\n2x2 (urgent, matched): BOTH={both} CLASSIFIER_ONLY={cls} REPORT_ONLY={rep} NEITHER={neither}")
print(f"  check: BOTH+REPORT_ONLY={both+rep} (=151?)  NEITHER+CLASSIFIER_ONLY={neither+cls} (=55?)")

# decomposition of the 55 report misses (primary: matched threshold + report named none of positive)
misses=[s for s in U if not gpt_urgent(s)]
reasoning=[s for s in misses if gpt_ment_any_pos(s)]
rem=[s for s in misses if not gpt_ment_any_pos(s)]
decoding=[s for s in rem if cls_detect(s)]
perception=[s for s in rem if not cls_detect(s)]
print(f"\nPRIMARY decomposition of {len(misses)} misses: REASONING={len(reasoning)} DECODING={len(decoding)} PERCEPTION={len(perception)}")

# by-finding for decoding misses (responsible = highest-scoring positive)
from collections import Counter
bycnt=Counter()
for s in decoding:
    pf=posf(s); bycnt[max(pf,key=lambda f:pa(s,f))]+=1
print("ED1_BY_FINDING:",dict(bycnt.most_common()))

# Claude decomposition (sensitivity)
def cl_urgent(s): return CA.get(s,"")=="urgent"
def cl_ment_any_pos(s): m=CM.get(s,{}); return any(m.get(f) for f in posf(s))
cmiss=[s for s in U if not cl_urgent(s)]
creas=[s for s in cmiss if cl_ment_any_pos(s)]; crem=[s for s in cmiss if not cl_ment_any_pos(s)]
cdec=[s for s in crem if cls_detect(s)]; cper=[s for s in crem if not cls_detect(s)]
print(f"CLAUDE_DECOMPOSITION: {len(cmiss)} misses -> REASONING={len(creas)} DECODING={len(cdec)} PERCEPTION={len(cper)}")

# exclude studies whose ONLY positive critical finding is calvarial fracture
def auroc(idx,sc):
    pos=[sc(S[i]) for i in idx if gt(S[i])]; neg=[sc(S[i]) for i in idx if not gt(S[i])]
    if not pos or not neg: return None
    allv=sorted([(sc(S[i]),gt(S[i])) for i in idx]); m=len(allv); rk=[0.]*m; k2=0
    while k2<m:
        j=k2
        while j+1<m and allv[j+1][0]==allv[k2][0]: j+=1
        for t in range(k2,j+1): rk[t]=(k2+j)/2+1
        k2=j+1
    return (sum(rk[t] for t in range(m) if allv[t][1])-len(pos)*(len(pos)+1)/2)/(len(pos)*len(neg))
Sx=[s for s in S if not (posf(s)==["calvarialfracture"])]
Ux=[s for s in Sx if gt(s)]
# matched threshold recomputed on the excluded set
sc2=sorted((urgsc(s) for s in Sx),reverse=True); fr=sum(gpt_urgent(s) for s in Sx)/len(Sx)
K2=round(fr*len(Sx)); THR2=sc2[K2-1]
rep_sens=sum(gpt_urgent(s) and gt(s) for s in Sx)/len(Ux)
cls_sens=sum(gt(s) and urgsc(s)>=THR2 for s in Sx)/len(Ux)
# bootstrap delta on excluded set
D=[]
for _ in range(2000):
    bs=[random.choice(Sx) for _ in Sx]; g=[i for i in bs if gt(i)]
    if not g: continue
    pf=sum(gpt_urgent(i) for i in bs)/len(bs); KK=int(pf*len(bs))
    top=sorted(bs,key=lambda i:-urgsc(i))[:KK]
    D.append(sum(gt(i) for i in top)/len(g)-sum(gpt_urgent(i) and gt(i) for i in bs)/len(g))
D=sorted(D); dl,dh=D[int(.025*len(D))],D[int(.975*len(D))]
exmiss=[s for s in Ux if not gpt_urgent(s)]
exreas=[s for s in exmiss if gpt_ment_any_pos(s)]; exrem=[s for s in exmiss if not gpt_ment_any_pos(s)]
exdec=[s for s in exrem if urgsc(s)>=THR2]; exper=[s for s in exrem if urgsc(s)<THR2]
print(f"\nEXCL calvarial-only: n={len(Sx)} urgent={len(Ux)}  Δsens={cls_sens-rep_sens:+.3f} [{dl:+.3f},{dh:+.3f}]  AUROC={auroc(list(range(len(Sx))),urgsc):.3f}")
print(f"  decomposition: {len(exmiss)} misses -> REASONING={len(exreas)} DECODING={len(exdec)} PERCEPTION={len(exper)}")

# FIG1A
print(f"\nFIG1A: finding=Subarachnoid hemorrhage score={pa('CQ500-CT-303','sah'):.3f} report='Study is unremarkable.'")
