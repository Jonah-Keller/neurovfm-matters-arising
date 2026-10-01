#!/usr/bin/env python
"""Judge validation (Q3). Two outputs:
  (1) PRELIMINARY automated cross-check: a rule-based mention detector over the prose,
      agreement + Cohen's kappa vs the Claude LLM judge, per finding. Not a substitute
      for human review, but flags gross judge errors now.
  (2) A ready-to-fill HUMAN review sheet: 100 sampled reports, prose text, the LLM
      judge's call per finding, and a blank human column — fill in an afternoon, then
      rerun this script pointing --human at it to get judge-vs-human agreement.
"""
import json, csv, re, random, sys
random.seed(7)
T = "/project/hipaa_visishslab/neurovfm_triage_audit"; C = f"{T}/outputs/cache_path_a"
OUT = f"{T}/outputs/reviewer_suite"
FIND = ["ich","iph","ivh","edh","sah","sdh","calvarialfracture","masseffect","midlineshift"]
# crude affirmative patterns (negation-guarded) for the rule-based cross-check
PAT = {
  "ich": r"(intracranial |intra-?axial )?(hemorrhage|haemorrhage|hematoma|bleed)",
  "iph": r"(intra-?parenchymal|parenchymal|intra-?axial) (hemorrhage|haemorrhage|hematoma)",
  "ivh": r"intraventricular (hemorrhage|blood|extension)",
  "edh": r"(epidural|extradural) (hematoma|haematoma|hemorrhage|collection)",
  "sah": r"subarachnoid (hemorrhage|haemorrhage|blood)",
  "sdh": r"subdural (hematoma|haematoma|hemorrhage|collection)",
  "calvarialfracture": r"(calvari|skull|frontal bone|parietal bone|temporal bone|occipital bone).{0,20}fracture|fracture.{0,20}(calvari|skull)",
  "masseffect": r"mass effect",
  "midlineshift": r"midline shift|shift of (the )?midline|midline.{0,15}shift",
}
NEG = r"(no |without |negative for |no evidence of |absence of )"
def rule_hit(text, f):
    t = text.lower()
    for m in re.finditer(PAT[f], t):
        a = max(0, m.start()-22)
        if not re.search(NEG + r"[\w ,]{0,22}$", t[a:m.start()]): return True
    return False

prose = {json.loads(l)["study"]: json.loads(l).get("findings","") for l in open(f"{C}/path_b_triage.jsonl") if l.strip()}
judge = {json.loads(l)["study"]: json.loads(l)["mentioned"] for l in open(f"{C}/prose_hit_claude.jsonl") if l.strip()}
studies = [s for s in judge if s in prose]

# (1) rule vs judge agreement + kappa
print("== Preliminary: rule-based vs LLM-judge agreement ==")
print(f"{'finding':<17}{'agree%':>8}{'kappa':>8}{'judge+':>8}{'rule+':>8}")
for f in FIND:
    a=b=c=d=0
    for s in studies:
        j = bool(judge[s].get(f, False)); r = rule_hit(prose[s], f)
        if j and r: a+=1
        elif j and not r: b+=1
        elif r and not j: c+=1
        else: d+=1
    n=a+b+c+d; po=(a+d)/n
    pe=((a+b)*(a+c)+(c+d)*(b+d))/(n*n)
    kappa=(po-pe)/(1-pe) if pe<1 else 1.0
    print(f"{f:<17}{100*po:>7.1f}{kappa:>8.2f}{a+b:>8}{a+c:>8}")

# (2) human review sheet (100 sampled reports, wide)
if "--human" in sys.argv:
    hp = sys.argv[sys.argv.index("--human")+1]
    hum = {r["study"]: r for r in csv.DictReader(open(hp))}
    print("\n== judge vs HUMAN agreement ==")
    for f in FIND:
        a=b=c=d=0
        for s, r in hum.items():
            if f"human_{f}" not in r or r[f"human_{f}"].strip()=="" or s not in judge: continue
            h = r[f"human_{f}"].strip() in ("1","y","yes","true"); j = bool(judge[s].get(f,False))
            if j and h: a+=1
            elif j and not h: b+=1
            elif h and not j: c+=1
            else: d+=1
        n=a+b+c+d
        if n: print(f"  {f:<17} agree={100*(a+d)/n:.1f}%  (n={n})")
    sys.exit(0)

sample = random.sample(studies, min(100, len(studies)))
with open(f"{OUT}/judge_review_sheet.csv", "w", newline="") as fh:
    cols = ["study","prose_excerpt"] + [f"judge_{f}" for f in FIND] + [f"human_{f}" for f in FIND]
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
    for s in sample:
        row = {"study": s, "prose_excerpt": re.sub(r"\s+"," ",prose[s])[:800]}
        for f in FIND:
            row[f"judge_{f}"] = int(bool(judge[s].get(f, False))); row[f"human_{f}"] = ""
        w.writerow(row)
print(f"\nwrote human review sheet (100 reports) -> {OUT}/judge_review_sheet.csv")
print("Fill the human_<finding> columns (1/0), then: judge_validation.py --human <that csv>")
