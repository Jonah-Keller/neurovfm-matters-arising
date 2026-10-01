#!/usr/bin/env python
"""Fill the manuscript tokens that are computable now (run-level replace preserves formatting).
Pending tokens (GPU ablation, their-paper, their-list, admin) are left as {{...}} and reported.
Usage: fill_docx.py <in.docx> <out.docx>
"""
import sys, docx
inp, out = sys.argv[1], sys.argv[2]
FILL = {
    "MATCHED_THRESHOLD": "0.98",
    "BOTH_CAUGHT": "134", "CLASSIFIER_ONLY": "17", "REPORT_ONLY": "17", "NEITHER": "38",
    "REASONING_N": "5", "DECODING_N": "13", "PERCEPTION_N": "37",   # matched-threshold PRIMARY (per token key)
    "CLAUDE_DECOMPOSITION": "4 reasoning, 11 decoding and 33 perception, of 48 misses",
    "ED1_BY_FINDING": "intraparenchymal hemorrhage (3), intracranial hemorrhage (3), "
                      "calvarial fracture (3), subarachnoid hemorrhage (2), subdural hematoma (1) "
                      "and mass effect (1)",
    "URGENCY_SENSITIVITY_RESULT": "the sensitivity difference was unchanged (0.000, 95% CI −0.030 to 0.030)",
    "ED2_URGENCY_SUMMARY": "After excluding the four studies whose only critical finding was "
                           "calvarial fracture (n = 468, 202 urgent), the sensitivity difference "
                           "remained 0.000 (95% CI −0.030 to 0.030; AUROC 0.948) and the 51 "
                           "misses decomposed as 5 reasoning, 12 decoding and 34 perception",
    "FIG1A_FINDING": "subarachnoid hemorrhage", "FIG1A_SCORE": "0.99",
    "FIG1A_REPORT_TEXT": "Study is unremarkable.",
    "SOFTWARE_VERSIONS": "Python 3.10, PyTorch 2.5.0 (CUDA 12.4), FlashAttention 2.6.3, NumPy and SciPy",
}
# left as {{...}} on purpose (pending): ABLATION_RESULT, ED2_ABLATION_SUMMARY, DETERMINISM_RESULT,
# THEIR_ED9D_INDICATION_EFFECT, COVERAGE_SUPP2D, CLAUDE_MODEL_VERSION, ED3_N_CASES,
# ED3_CASE_DESCRIPTIONS, FUNDING_STATEMENT

d = docx.Document(inp)
def paras(doc):
    for p in doc.paragraphs: yield p
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs: yield p
filled = {}
for p in paras(d):
    for r in p.runs:
        for tok, val in FILL.items():
            s = "{{" + tok + "}}"
            if s in r.text:
                r.text = r.text.replace(s, val); filled[tok] = filled.get(tok, 0) + 1
d.save(out)
import re, zipfile
remaining = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}",
               zipfile.ZipFile(out).read("word/document.xml").decode("utf-8", "ignore")))
print("FILLED:", {k: filled.get(k, 0) for k in FILL})
missed = [k for k in FILL if not filled.get(k)]
if missed: print("WARNING not found (maybe split):", missed)
print("STILL PENDING (left as tokens):", sorted(remaining))
print("saved", out)
