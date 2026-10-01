#!/usr/bin/env python
"""GPT-5 on CQ500 (public data only): (1) triage SCREENER acuity, (2) second-LLM JUDGE
of the 9 findings. One call per study. Resumable, threaded. Never touches in-house PHI.
Out: outputs/gpt_cq500/gpt.jsonl  {study, acuity, mentioned:{...}}
"""
import json, os, re, urllib.request, concurrent.futures as cf, time
T = "/project/hipaa_visishslab/neurovfm_triage_audit"; C = f"{T}/outputs/cache_path_a"
OUT = f"{T}/outputs/gpt_cq500"; os.makedirs(OUT, exist_ok=True)
KEY = open(os.path.expanduser("~/.openai_key")).read().strip()
FIND = ["ich","iph","ivh","edh","sah","sdh","calvarialfracture","masseffect","midlineshift"]
prose = {json.loads(l)["study"]: json.loads(l).get("findings","") for l in open(f"{C}/path_b_triage.jsonl") if l.strip()}
outp = f"{OUT}/gpt.jsonl"
done = set()
if os.path.exists(outp):
    done = {json.loads(l)["study"] for l in open(outp) if l.strip()}
todo = [s for s in prose if s not in done]
print(f"{len(prose)} studies, {len(todo)} to do", flush=True)

SYS = ("You are a neuroradiology triage screener and report auditor. Given a generated CT-head "
       "report, return STRICT JSON: {\"acuity\":\"urgent\"|\"routine\", \"mentioned\":{"
       "\"ich\":bool,\"iph\":bool,\"ivh\":bool,\"edh\":bool,\"sah\":bool,\"sdh\":bool,"
       "\"calvarialfracture\":bool,\"masseffect\":bool,\"midlineshift\":bool}}. "
       "acuity=urgent if any acute/critical intracranial finding needs immediate attention. "
       "mentioned[x]=true only if the report AFFIRMATIVELY states finding x (not negated). No prose.")

def call(study):
    body = json.dumps({"model":"gpt-5-2025-08-07",
        "messages":[{"role":"system","content":SYS},
                    {"role":"user","content":prose[study][:6000] or "(empty report)"}],
        "max_completion_tokens":2000,
        "response_format":{"type":"json_object"}}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
                headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=120))
            txt = r["choices"][0]["message"]["content"]
            d = json.loads(txt)
            return {"study":study, "acuity":str(d.get("acuity","")).lower(),
                    "mentioned":{f:bool(d.get("mentioned",{}).get(f,False)) for f in FIND}}
        except Exception as e:
            if attempt==3: return {"study":study, "error":str(e)[:150]}
            time.sleep(2*(attempt+1))

t0=time.time(); n=0
with open(outp,"a") as fh, cf.ThreadPoolExecutor(max_workers=6) as ex:
    for res in ex.map(call, todo):
        fh.write(json.dumps(res)+"\n"); fh.flush(); n+=1
        if n%25==0: print(f"  {n}/{len(todo)}  ({time.time()-t0:.0f}s)", flush=True)
print(f"done {n} -> {outp}", flush=True)
