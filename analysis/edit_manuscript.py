#!/usr/bin/env python
"""Flip the decomposition to the finding-specific (>0.5) PRIMARY definition and fill all
computable tokens. Rewrites the four definition-coupled paragraphs (main-text decomposition,
Methods classification, Fig 1 legend, ED Fig 1 legend) with inline final values; token-fills
the rest. Pending tokens stay as {{...}}.
Usage: edit_manuscript.py <in.docx> <out.docx>
"""
import sys, docx
inp, out = sys.argv[1], sys.argv[2]
d = docx.Document(inp)

# ---- token fills in non-rewritten paragraphs ----
FILL = {
    "BOTH_CAUGHT": "134", "NEITHER": "38", "CLASSIFIER_ONLY": "17", "REPORT_ONLY": "17",
    "URGENCY_SENSITIVITY_RESULT": "the sensitivity difference was unchanged (0.000, 95% CI −0.030 to 0.030)",
    "ED2_URGENCY_SUMMARY": "After excluding the four studies whose only critical finding was "
        "calvarial fracture (n = 468, 202 urgent), the sensitivity difference remained 0.000 "
        "(95% CI −0.030 to 0.030; AUROC 0.948) and the 51 misses decomposed as 37 decoding, "
        "9 perception and 5 reasoning under the primary definition",
    "SOFTWARE_VERSIONS": "Python 3.10, PyTorch 2.5.0 (CUDA 12.4), FlashAttention 2.6.3, NumPy and SciPy",
    "CLAUDE_MODEL_VERSION": "Claude Sonnet 4.5 (claude-sonnet-4-5)",
    "ED3_N_CASES": "Six",
    "ED3_CASE_DESCRIPTIONS": "The examples span subarachnoid hemorrhage, intraparenchymal "
        "hemorrhage, subdural hematoma, intracranial hemorrhage, calvarial fracture and mass "
        "effect; in each the classifier scored the finding above 0.96 while the report read as normal.",
    "COVERAGE_SUPP2D": "all head-CT-assessable critical findings on the list (16 of its 40 "
        "entries, including hemorrhage, acute stroke, herniation, hydrocephalus, mass effect, "
        "edema, aneurysm, arteriovenous malformation, venous sinus thrombosis, vascular dissection "
        "and occlusion, skull fracture, pneumocephalus, abscess and foreign body); the remaining "
        "entries are spinal or soft-tissue findings outside the scope of a non-contrast head CT",
    "THEIR_ED9D_INDICATION_EFFECT": "a small reduction in NeuroVFM’s three-tier acuity accuracy "
        "(approximately 0.80 to 0.76)",
    "FUNDING_STATEMENT": "",
    "DATE_SENT_TO_HOLLON": "October 2, 2026",
    "DECODING_N": "40", "WORD_COUNT": "1118",
    "ABLATION_RESULT": "38 of the 40 decoding misses persisted under each of a “head trauma” and a "
        "“headache” indication (37 under both), the report pipeline’s sensitivity for urgent studies "
        "did not improve (0.733 with no indication, 0.728 with head trauma, 0.694 with headache), and "
        "the classifier’s was unchanged at 0.733",
    "ED2_ABLATION_SUMMARY": "no indication, 40 decoding, 10 perception and 5 reasoning of 55 misses; "
        "head trauma, 40 decoding, 10 perception and 6 reasoning of 56; headache, 47 decoding, 11 "
        "perception and 5 reasoning of 63; 38 of the 40 decoding misses in the main analysis persisted "
        "under each indication",
    "DETERMINISM_RESULT": "all 40 reproduced verbatim, confirming the omissions are deterministic "
        "under the model’s greedy decoding rather than sampling artefacts",
}
TEXT_REPLACE = {"October __, 2026": "October 14, 2026",
    "while 17 were caught only by the classifier and 17 only by the report (Fig. 1c).":
        "while 17 were caught only by the classifier and 17 only by the report.",
    "missed by both readouts (Fig. 1d).": "missed by both readouts."}

# ---- full paragraph rewrites (match by unique prefix) -> (new_text, bold_prefix_or_None) ----
R_MAIN = ("The misses of the report pipeline show where information was lost. Of the 55 urgent "
    "studies it missed, in 40 the classifier had already scored the missed finding above 0.5 "
    "(median 0.92) while the report named none of the study’s critical findings (Fig. 1c). Most of "
    "these silent reports read as explicitly normal, for example, “Study is unremarkable.” They "
    "were complete outputs rather than truncated or empty generations, and the language model had "
    "received the same bone window as the classifier. The omitted findings included calvarial "
    "fracture, intraparenchymal hemorrhage, subdural hematoma and mass effect. A normal-reading "
    "report is more consequential than a missing flag, because it reassures and moves a scan down "
    "the worklist. Under the original evaluation these studies would count as failures of "
    "perception, although the encoder had represented the finding. The remaining 15 misses are "
    "decomposed in Extended Data Fig. 1.")

R_METHODS = ("Each urgent study was classified as detected or missed by each readout, giving a "
    "two-by-two table. A study missed by the report pipeline was a reasoning miss if its report "
    "named at least one of the study’s positive critical findings. Otherwise, it was a decoding "
    "miss if the classifier scored the highest-scoring positive finding above 0.5 while the report "
    "was silent on all of the study’s positive findings, and a perception miss if that score was "
    "0.5 or below. Defining report silence across all positive findings, rather than a single "
    "responsible finding, is conservative because it avoids selecting the finding most favourable "
    "to a decoding classification. As a sensitivity analysis, we reclassified misses using the "
    "matched triage threshold in place of the 0.5 score, which gave 13 decoding, 37 perception and "
    "5 reasoning misses (Extended Data Fig. 1). Every decoding-miss report was inspected for empty, "
    "truncated or errored output.")

R_FIG1 = ("Fig. 1. ", "NeuroVFM’s diagnostic classifier detects most urgent findings that its "
    "written reports omit, so report-based evaluation does not isolate perception. a, The released "
    "NeuroVFM system and the change we evaluated. One frozen encoder feeds two readouts that do not "
    "share information. In the original study, perception and triage were evaluated through the "
    "report path, in which a 14-billion-parameter language model writes findings that GPT-5 reads "
    "to assign acuity (orange). We also read the diagnostic classifier (about 0.95 million "
    "parameters) directly (blue). Shown for one CQ500 study with subarachnoid hemorrhage: the "
    "classifier scored the finding at 0.99 and flagged the study, whereas the generated report read "
    "“Study is unremarkable.” and the study was not escalated. b, Sensitivity for urgent studies "
    "versus fraction of studies flagged (n = 472, 206 urgent). Blue curve and band, the "
    "classifier’s highest score across the nine critical findings used directly as a triage score, "
    "with 95% CI (AUROC 0.949, 95% CI 0.928–0.967). Orange point, the report pipeline (sensitivity "
    "0.733 at a flag rate of 0.341). Blue point, the classifier at the same flag rate, a threshold "
    "chosen without labels; the difference in sensitivity was 0.000 (95% CI −0.029 to 0.030). c, "
    "The report pipeline missed 55 urgent studies. In 40 of them the report was silent on every "
    "critical finding yet the classifier had already scored the study’s finding above 0.5; each "
    "point is that classifier score (dotted line, 0.5; tick, median 0.92). The remaining 15 misses "
    "— 10 in which the classifier score was also 0.5 or below, and 5 in which the report named a "
    "finding that was not escalated to urgent — are shown in Extended Data Fig. 1. Confidence "
    "intervals in b are from 2,000 study-level bootstrap resamples.")

R_ED1 = ("Extended Data Fig. 1. ", "Decomposition of report-pipeline misses under alternative "
    "definitions and screening models. a, Decomposition of the 55 misses under the primary "
    "definition (classifier score above 0.5 on the highest-scoring positive finding, report silent "
    "on all positive findings: 40 decoding, 10 perception, 5 reasoning) and under the sensitivity "
    "definition (classifier flag at the matched triage threshold: 13 decoding, 37 perception, 5 "
    "reasoning). b, The same decomposition with Claude as the screening model (34 decoding, 10 "
    "perception, 4 reasoning of 48 misses under the primary definition; 11 decoding, 33 perception, "
    "4 reasoning under the sensitivity definition). Acuity agreement between the two screeners was "
    "96.6%. c, Decoding misses by critical finding (calvarial fracture 9, intraparenchymal "
    "hemorrhage 8, intracranial hemorrhage 8, subdural hematoma 5, mass effect 5, subarachnoid "
    "hemorrhage 3, epidural hematoma 2). d, Fraction of generated reports reading as normal among "
    "urgent (23%) and non-urgent (96%) studies. e, Agreement on whether each reference finding was "
    "mentioned, between GPT-5 and Claude as judges (mean κ 0.97) and between each judge and a "
    "rule-based detector (κ 0.92 or higher for hemorrhage findings).")

def set_para(p, text, bold_prefix=None):
    for r in list(p.runs): r._element.getparent().remove(r._element)
    if bold_prefix:
        rb = p.add_run(bold_prefix); rb.bold = True
    p.add_run(text)

def para_fulltext(p): return "".join(r.text for r in p.runs)

R_PARITY = ("Read directly, the classifier separated urgent from non-urgent studies with an area "
    "under the receiver operating characteristic curve of 0.949 (95% CI 0.928–0.967; Fig. 1b). At "
    "the report pipeline's flag rate, the two readouts detected the same fraction of urgent studies "
    "(73.3% each; difference 0.000, 95% CI −0.029 to 0.030) — equivalent sensitivity, which we note "
    "is not a claim that the classifier is the better triager. They did not, however, make the same "
    "errors: 17 urgent studies were caught only by the classifier and 17 only by the report "
    "pipeline, so each readout missed studies the other caught, and generation adds value for some "
    "findings. Because the two readouts share one encoder yet err differently, the misses of the "
    "report pipeline cannot be read as failures of the encoder, which we examine next.")

rewrites = [
    ("Read directly, the classifier separated urgent from non-urgent", R_PARITY, None),
    ("The misses of the report pipeline show where information", R_MAIN, None),
    ("Each urgent study was classified as detected or missed", R_METHODS, None),
    ("NeuroVFM’s diagnostic classifier detects most urgent", R_FIG1[1], R_FIG1[0]),
    ("Decomposition of report-pipeline misses under alternative", R_ED1[1], R_ED1[0]),
]
done_rw = set()
for p in d.paragraphs:
    ft = para_fulltext(p)
    for key, newtext, bold in rewrites:
        if key in ft and key not in done_rw:
            set_para(p, newtext, bold); done_rw.add(key)
# token fills + literal text replacements (run-level)
for p in d.paragraphs:
    for r in p.runs:
        for tok, val in FILL.items():
            s = "{{" + tok + "}}"
            if s in r.text: r.text = r.text.replace(s, val)
        for a, b in TEXT_REPLACE.items():
            if a in r.text: r.text = r.text.replace(a, b)
d.save(out)
import re, zipfile
rem = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", zipfile.ZipFile(out).read("word/document.xml").decode("utf-8","ignore"))))
print("rewrote:", sorted(done_rw))
print("STILL PENDING:", rem)
print("saved", out)
