# Writing handoff — NeuroVFM Matters Arising + standalone paper

Consolidated methods, final numbers, and the exact claims to make. Companion to the per-repo `OUTLINE.md`, `REVIEWER_ANSWERS.md`, `AUDITOR_RESPONSE*.md`. One item pending: the indication ablation (GPU job `99566277`, running) — its result drops into §MA-Results item (f).

---

# PAPER 1 — Matters Arising (*Nature Medicine*)

## Focus (one sentence)
NeuroVFM's urgent triage misses are **decoding failures, not perception failures** — the calibrated diagnostic head already matches the full prose+screener pipeline on triage, and the misses are studies where the head is confident but the generated report reads normal. **Deployment choice (which readout you trust), not model scale, governs triage safety.**

## Lead + mechanism
- **Lead = missing baseline, framed as parity/non-inferiority.** The diagnostic head's zero-parameter score triages at **AUROC 0.949 (95% CI 0.928–0.968)**; sensitivity is **comparable** at a matched flag rate (**+0.034, 95% CI −0.009 to +0.065** — crosses zero), at a fraction of the compute (82-way linear head vs 14B-param generation + a GPT-5 call). We do **not** claim a sensitivity win.
- **Mechanism = decoding/false-normal.** Of 48 urgent misses, **34 (71%)** are decoding (prose silent, head confident on the *specific* missed finding), 10 perception, 4 reasoning. All 34 are **genuine outputs** (0 empty/truncated); **21/34 explicit false-normals** ("Study is unremarkable"), the rest named other (often chronic) findings. The decoder does **not** blanket-default to normal: it false-normals **23% of urgent** vs correctly calls **96% of non-urgent** normal — selective false-normalcy on exactly the studies the head flags. Median head score on the missed finding **0.93**. Holds with **GPT-5** as screener (73% decoding).

## Methods (for the Methods/Supplement)
- **Cohort:** CQ500 (Chilamkurthy 2018), 472 studies joined to reader consensus; 206 (44%) urgent by any of 9 critical findings.
- **Two readouts, shared frozen encoder, released weights:** Path A = shipped diagnostic head `mlinslab/neurovfm-dx-ct` (82 CT dx); Path B = released `mlinslab/neurovfm-llm` generating free-text findings (deterministic beam search: `do_sample=False, num_beams=4`), then a triage screener. **Both readouts received the same pooled diagnostic series per study** (`cq500_index.series_dirs`), each via its path's standard preprocessor; `clinical_context=""` (image-only). The original cache used a **Claude** screener/mention-judge; we re-ran the screener with **GPT-5** (the authors' model) for faithfulness.
- **Definitions:** urgent study = consensus-positive for any of {ich, iph, ivh, edh, sah, sdh, calvarial fracture, mass effect, midline shift}. Miss = urgent study not escalated by the screener. Decoding = miss + prose silent on the specific finding + head score > 0.5; perception = miss + head ≤ 0.5; reasoning = prose named it but screener didn't escalate.
- **Zero-parameter triage score:** per study, max head probability over the critical labels; sensitivity vs flag rate swept; compared to the prose pipeline's single operating point. CI = bootstrap re-selecting the matched threshold within each resample (2000×); held-out = 5-fold (Methods only, Δ +0.020 ± 0.125).
- **Judge validation (three methods):** rule-based detector κ ≥ 0.92 on hemorrhages; GPT-5 second judge mean **κ 0.97**; 100-report human sheet available.
- **Crosswalk:** 9 CQ500 findings → 82 labels (`mapping/cq500_to_neurovfm_ct.yaml`, max-prob).

## Results — final numbers
| claim | value |
|---|---|
| urgent studies / missed / decoding | 206 / 48 / **34 (71%)** |
| zero-param triage AUROC | **0.949 [0.928–0.968]** |
| sensitivity Δ at matched flag rate | **+0.034 [−0.009, +0.065]** (parity) |
| decomposition (perc/dec/reas) | 10 / 34 / 4 |
| false-normal among decoding | 21/34 explicit; 0 empty/truncated |
| normal-read rate urgent vs non-urgent | 23% vs 96% |
| median head score on missed finding | 0.93 |
| screener-invariance (GPT-5) | 55/206 missed, **73% decoding**, 96.6% acuity agreement |
| judge κ (GPT-5 vs Claude) | **0.97** (rule-based ≥0.92) |
| CQ500 per-finding AUROC | fracture 0.936, ich 0.945, iph 0.940, sdh 0.963, sah 0.930, mass effect 0.954 |
| calibration (pooled ECE) | 0.251 → report "high **score**", not probability |
| ASNR critical-list coverage | 17/18 (gap: venous sinus thrombosis) — confirm vs ref 17 |
| generation | deterministic (greedy beam search) |
| **(f) indication ablation** | **PENDING — job 99566277** (do the 34 persist with an indication?) |

## Structure (the agreed 6)
1. Summary + the two concerns. 2. Task fit (triage = discrete decision over a fixed list). 3. Missing baseline (0.949; comparable sensitivity). 4. Mechanism (34/48 false-normal; median 0.93; GPT-5-stable). 5. Indication ablation as robustness check. 6. Closing: match the readout to the task + honest concession (prose helps for out-of-ontology / incidental / laterality-size / synthesis).

## Caveats to state
Single public dataset; 44% prevalence vs 13% prospective (limitations sentence; optional reweighted flag-rate ED panel); external calibration poor (discrimination transfers, calibration doesn't); screener substitution disclosed (GPT-5 re-run resolves it).

---

# PAPER 2 — Standalone (neuroradiology/neurosurgery; *Radiology: AI* / AJNR)

## Focus
A neuroimaging foundation model's diagnostic head **generalizes to an external institution**, but clinical performance is **governed by deployment** — input series/recon selection materially changes perception, and a reproducible offline pipeline is needed to run it at scale on routine PACS. Plus a structured, calibrated readout rendered from the head vs free-text prose.

## Methods
In-house cohort (de-identified RADAR/Project91 head CTs), 490 primary axial-brain CTs, 343 paired with radiologist reports. Three token-aligned layers: Path-A 82 dx; TotalSegmentator 16 volumes; report-derived 17 findings (negation-mined). Contributions M1 offline/at-scale LSF pipeline, M2 multi-slice DICOM→NIfTI fix, M3 multi-series/bone-kernel routing, M4 report-mined negatives, M5 crosswalk, M6 render-from-head, M7 anatomy concordance.

## Results
| | value |
|---|---|
| external validation mean AUROC | **0.82** (11 findings) vs in-domain 0.925 |
| per-finding | hydrocephalus 0.96, ivh 0.93, iph 0.92, mass effect 0.86, sah 0.83, any-ich 0.79, acute-infarct 0.79 |
| input-conditioned perception (fracture) | 0.14 (soft-tissue) → 0.28 (multi-series); per-case 0.01→0.80 |
| rendered-report vs actual report | macro-F1 0.44 at naive 0.5 threshold → the **operating-point dial** matters |
| anatomy concordance (M7) | PENDING (zero-GPU; both tables on disk) |

## Figures
Fig 1 external AUROC; Fig 2 original-vs-improved (bone-kernel); Fig 3 Path-A × anatomy; Fig 4 pipeline. Fracture appears **only here**, after a vault-only relabel.

---

# Shared assets
- **MA repo:** github.com/Jonah-Keller/neurovfm-matters-arising — `AUDITOR_RESPONSE.md`, `AUDITOR_RESPONSE_2.md`, `REVIEWER_ANSWERS.md`, figures, `data_deid/` (CQ500 public), `analysis/` (reviewer_suite, reviewer_ci2, gpt_cq500, judge_validation, followup, path_b_indication).
- **Standalone repo:** github.com/Jonah-Keller/neurovfm-external-validation — `OUTLINE.md`, `PAPER_SUMMARY.md`, `fig1_auroc.png`, `data_deid/`.
- **Results dashboard:** `RESULTS_REVIEW.html` (both repos).

# Open items
1. **Indication ablation** (running) → fills MA mechanism robustness.
2. ASNR ref-17 exact list (confirm coverage).
3. Anatomy concordance (M7) for the standalone (cheap).
4. Optional: human judge adjudication (κ already 0.97); bootstrap CIs on in-house AUROCs.
5. Awaiting your **figure-guideline code + docx** (push to `incoming/`) to restyle figures and start prose.
