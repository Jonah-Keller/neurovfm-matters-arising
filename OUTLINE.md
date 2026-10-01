# Matters Arising — outline

**Target:** *Nature Medicine*, Matters Arising on NeuroVFM (Kondepudi et al., *Nat Med* 2026).
**Format hard limits:** ≤1,200 words main text; 1–2 small figures/tables; ≤3 Extended Data items; ≤15 refs; competing-interests + author-contributions statements; reporting summary (new data). Measured tone.
**Author contact:** original authors contacted; declined to engage — state this at submission (satisfies the pre-submission contact requirement).

---

## One-line message (the "abstract" paragraph, non-specialist)
In radiology AI it matters not only *which* foundation model you deploy but *how* you read its outputs. NeuroVFM's urgent triage misses were attributed to the encoder failing to *perceive* findings; we show instead that the encoder usually *did* perceive them — the free-text report-generation path dropped them. Rendering the report through a structured schema **from the model's calibrated diagnostic head** recovers these misses and outperforms free-text generation. The lesson generalizes: deployment design, not just model scale, governs clinical safety.

## Core scientific claim
NeuroVFM's two paths share one frozen encoder: Path A (calibrated 82-dx diagnostic head) and Path B (findings LLM → screener → triage). The authors report that **all 21 urgent prospective misses were cases where the generated prose was silent**, attributing this to *perception* (coarse tokens). We re-examine that attribution on contemporaneous data (CQ500 + the released model) and find the misses are predominantly a **prose-generation bottleneck**, not an encoder perception limit: among Path-B silent misses, Path-A's calibrated probability on the true diagnosis is **shifted high** (encoder saw it). A schema that renders findings from Path A recovers them.

## Structure (≤1,200 words)
1. **Opening paragraph** (message, as above) — ~120 w.
2. **The claim under examination** — restate the authors' perception attribution of the 21 silent misses; why the two paths never communicating makes this testable. ~200 w.
3. **Re-analysis** — Path-A probability on the true dx among Path-B silent misses vs a true-negative null (CQ500 consensus ground truth). Dissociation statistic. ~300 w.
4. **The fix: render from the diagnostic head** — the prose schema (tokenized calibrated heads → templated report, honest gating of the uncalibrated ~70 heads); finding-recovery vs free-text at a sensible operating point. ~300 w.
5. **Implication** — "how you use the tool" as a first-class safety lever; not a flaw in the encoder but in the readout. Measured, constructive. ~200 w.

## Figures (1 main + Extended Data)
- **Figure 1 — the dissociation and the fix** (single composite):
  - **(a)** schematic: frozen encoder → Path A (calibrated differential) vs Path B (prose → screener → triage); annotate "paths never communicate."
  - **(b)** core result: distribution of **Path-A probability on the true diagnosis among Path-B silent misses** (urgent, prose-silent) vs a matched true-negative null. Right-shift = perception succeeded. Report AUROC/effect size + n.
  - **(c)** recovery: at a fixed Path-A operating point, **fraction of Path-B silent misses recovered** by schema rendering; bar vs free-text prose finding-capture.
- **Extended Data 1** — worked example: a Path-B report that went silent on an urgent finding, beside the schema-rendered report that captured it (de-identified CQ500 case).
- **Extended Data 2** — render "dial": sensitivity/specificity vs per-dx probability threshold (the operating-point knob).
- **Extended Data 3** — per-finding table: Path-B prose-hit rate vs Path-A-confident rate, on CQ500-urgent findings.

## Analysis to complete (checklist)
- [x] Path-A diagnostic head runnable offline on local weights (pipeline M1/M2).
- [x] Crosswalk CQ500 findings → NeuroVFM 82 labels (`mapping/cq500_to_neurovfm_ct.yaml`).
- [x] Harness: `analysis/phase1_disagreement.py` (dissociation), `phase3_render.py` + `render_prose_v3.py` (schema render).
- [ ] **Build the cache at scale on CQ500:** Path-A probs on all CQ500; Path-B prose (NeuroVFM VLM) + screener triage on all CQ500 (public data → external LLM screener OK). *Current `outputs/prose_reports.txt` has only 3 studies — this is the remaining compute.*
- [ ] Run `phase1_disagreement.py` → Figure 1b + effect size.
- [ ] Run `phase3_render.py` at chosen threshold → Figure 1c + Extended Data 1/2/3.

## Repo layout (this directory)
- `manuscript.md` (draft), `OUTLINE.md` (this), `figures/`, `data_deid/` (CQ500 consensus + derived tables only — CQ500 is CC-BY-NC-SA, keep raw out), `analysis/` (symlink/copy of the phase1/phase3 scripts actually used).
- Keep **only CQ500-derived + model-output** artifacts here; no in-house PHI (that lives in the standalone-paper repo's secured space).
