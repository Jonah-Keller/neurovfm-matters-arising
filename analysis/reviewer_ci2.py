import json, csv, random
random.seed(42)
T="/project/hipaa_visishslab/neurovfm_triage_audit"; C=f"{T}/outputs/cache_path_a"
URGENT={"ich":["intracranial_hemorrhage"],"iph":["intraparenchymal_hemorrhage"],
 "ivh":["intraventricular_hemorrhage"],"edh":["epidural_hematoma"],
 "sah":["aneurysmal_subarachnoid_hemorrhage","traumatic_subarachnoid_hemorrhage"],
 "sdh":["acute_subdural_hematoma","subacute_chronic_subdural_hematoma"],
 "calvarialfracture":["displaced_skull_fracture","nondisplaced_skull_fracture"],
 "masseffect":["brain_mass_effect"],"midlineshift":["midline_shift"]}
def ld(p): return {json.loads(l)["study"]:json.loads(l) for l in open(p) if l.strip()}
probs=ld(f"{C}/path_a_probs.jsonl"); acu=ld(f"{C}/acuity_claude.jsonl")
def tru(v):
    try: return float(v)>=0.5
    except: return False
cons={}; rdr=csv.DictReader(open(f"{T}/data/cq500_consensus.csv")); idc=rdr.fieldnames[0]
for r in rdr: cons[r[idc].strip()]={f:tru(r.get(f,0)) for f in URGENT if f in r}
U=[];G=[];P=[]
for s in probs:
    if s not in cons: continue
    U.append(max(max((probs[s]["probs"].get(l,0) for l in URGENT[f]),default=0) for f in URGENT))
    G.append(any(cons[s].get(f,False) for f in URGENT))
    P.append(acu.get(s,{}).get("acuity","").lower()=="urgent")
n=len(U); ng=sum(G)
def auroc(idx):
    pos=sum(1 for i in idx if G[i]); neg=len(idx)-pos
    if pos==0 or neg==0: return None
    av=sorted(((U[i],G[i]) for i in idx),key=lambda x:x[0]); m=len(av); ranks=[0.]*m; k=0
    while k<m:
        j=k
        while j+1<m and av[j+1][0]==av[k][0]: j+=1
        for t in range(k,j+1): ranks[t]=(k+j)/2.+1
        k=j+1
    sp=sum(ranks[t] for t in range(m) if av[t][1])
    return (sp-pos*(pos+1)/2)/(pos*neg)
def delta(idx):
    m=len(idx); gl=[i for i in idx if G[i]]
    if not gl: return None
    pf=sum(P[i] for i in idx)/m
    ps=sum(P[i] and G[i] for i in idx)/len(gl)
    K=int(pf*m); top=sorted(idx,key=lambda i:-U[i])[:K]
    return sum(G[i] for i in top)/len(gl)-ps
allidx=list(range(n))
print(f"n={n} urgent={ng}")
print(f"point: AUROC={auroc(allidx):.3f}  dsens={delta(allidx):+.3f}")
sh=allidx[:]; random.shuffle(sh); folds=[sh[i::5] for i in range(5)]; ds=[]
for fi in folds:
    te=set(fi); tr=[i for i in allidx if i not in te]
    pf=sum(P[i] for i in tr)/len(tr); K=int(pf*len(tr))
    thr=sorted((U[i] for i in tr),reverse=True)[K-1] if K>0 else 1.1
    tu=[i for i in fi if G[i]]
    if not tu: continue
    zp=sum(G[i] and U[i]>=thr for i in fi)/len(tu); pr=sum(G[i] and P[i] for i in fi)/len(tu)
    ds.append(zp-pr)
mm=sum(ds)/len(ds); sd=(sum((d-mm)**2 for d in ds)/len(ds))**.5
print(f"HELD-OUT 5-fold: dsens={mm:+.3f} +/- {sd:.3f}  folds={[round(d,3) for d in ds]}")
B=2000; A=[];D=[]
for _ in range(B):
    bs=[random.randrange(n) for _ in range(n)]
    a=auroc(bs); d=delta(bs)
    if a is not None: A.append(a)
    if d is not None: D.append(d)
def ci(x): x=sorted(x); return x[int(.025*len(x))],x[int(.975*len(x))]
al,ah=ci(A); dl,dh=ci(D)
print(f"BOOTSTRAP B={B}: AUROC 95%CI [{al:.3f},{ah:.3f}]  dsens 95%CI [{dl:+.3f},{dh:+.3f}]")
