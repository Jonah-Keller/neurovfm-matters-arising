# Comprehensive handoff — NeuroVFM Matters Arising (+ standalone)

Exhaustive methods + results reference for drafting and for figure design. All numbers are final and sourced to scripts in `neurovfm_triage_audit/analysis/`. **GPT-5 is the primary screener + mention judge; Claude is a sensitivity analysis.** Single denominator **N = 472**. One slot pending: indication ablation (running: jobs 99567839 trauma / 99567840 headache / 99567841 determinism).

---

## PART I — MATTERS ARISING

### 1. Thesis
NeuroVFM's urgent-triage misses are **decoding failures, not perception failures**: the frozen encoder's calibrated diagnostic head (Path A) already **matches the full prose+screener pipeline (Path B) on triage**, and the misses are studies where the head is confident but the generated report reads **normal**. The actionable claim: for a discrete triage decision over a fixed finding list, **read the calibrated head, don't parse generated prose** — deployment choice, not model scale, governs safety.

### 2. Data
- **Cohort:** CQ500 (Chilamkurthy et al., *Lancet* 2018), public. Kaggle mirror `crawford/qureai-headct` v2, cached in project space. 491 studies with reader consensus; **472** resolve to loadable DICOMs *and* a consensus row → the analysis denominator.
- **Ground truth:** CQ500 radiologist consensus (`reads.csv`). Nine findings treated as **urgent/critical**: intracranial hemorrhage (ich), intraparenchymal (iph), intraventricular (ivh), epidural (edh), subarachnoid (sah), subdural (sdh), calvarial fracture, mass effect, midline shift. A label is positive at consensus ≥ 0.5.
- **Prevalence:** **206/472 urgent (44%)** — vs 13% in NeuroVFM's prospective week (limitations sentence; optional flag-rate reweighting to 13% as Extended Data).

### 3. The two readouts (one frozen encoder, released weights)
Both paths consume the **same pooled diagnostic series per study** (`cq500_index.series_dirs(study)`), each via an **identical `StudyPreprocessor`**: resample to 1×1×4 mm, three CT windows — **brain (W80/L40), blood (W200/L80), bone (W2800/L600)** — tokenized and concatenated, **no series cap**, background-filtered, AB-MIL aggregation (order-invariant). Confirmed: the decoder received the **bone window** (bears on the fracture misses — it had the information).

- **Path A — diagnostic head** (`mlinslab/neurovfm-dx-ct`): attention-pooled gated-MLP (`attention_V`, `gating_V`, LayerNorm, MLP **768→384→82**), **952,264 parameters (0.95M)**, sigmoid-calibrated probabilities over **82 CT diagnoses**.
- **Path B — findings LLM** (`mlinslab/neurovfm-llm`): generates free-text findings, then a triage screener. Decoding is **deterministic greedy beam search**: `do_sample=False, num_beams=4, length_penalty=1.0, repetition_penalty=1.2, no_repeat_ngram_size=4, max_new_tokens=512, min_new_tokens=3`; system prompt "expert neuro-radiologist", **`clinical_context=""`** (image-only, matching Path A's image-only input). The screener consumes the prose and emits an acuity.
- **Screener + mention judge:** **GPT-5** (`gpt-5-2025-08-07`) is primary (the authors' screener model); **Claude** is the sensitivity analysis. Agreement between the two mention judges **κ = 0.97**; vs an independent rule-based detector **κ ≥ 0.92** on the hemorrhage findings.

### 4. Definitions (used everywhere)
- **Urgent study** = consensus-positive for any of the nine.
- **Miss** = urgent study the screener does not escalate (acuity ≠ urgent).
- **Responsible finding** = the consensus-positive urgent finding with the highest head score.
- **Decoding miss** = miss + prose **silent on the responsible finding** (judge: not mentioned) + head score on it **> 0.5**.
- **Perception miss** = miss + head score on the responsible finding **≤ 0.5**.
- **Reasoning miss** = miss + prose **named** the responsible finding but the screener did not escalate.
- **Zero-parameter urgency score** = max head probability over the NeuroVFM labels mapped to the nine critical findings (crosswalk `mapping/cq500_to_neurovfm_ct.yaml`, max-prob over candidates).

### 5. Statistics
- **Matched-flag-rate comparison:** choose the head's threshold so it flags the **same fraction of studies** as the prose pipeline — this uses **only the score distribution, no labels**, so the in-sample comparison carries **no optimism bias** (cleaner than a held-out split; the 5-fold is dropped). Report sensitivity difference + AUROC.
- **CI:** non-parametric **bootstrap (2000×)** over studies, **re-selecting the matched threshold within each resample**; 2.5/97.5 percentiles.
- **Decomposition** uses the GPT-5 screener (misses) and GPT-5 mention judge (silent/named); Claude as sensitivity.
- **Calibration:** reliability by decile, pooled over the nine findings, Expected Calibration Error.

### 6. RESULTS — primary (GPT-5) with Claude sensitivity

**6a. The missing baseline (headline).**
| | GPT-5 (primary) | Claude (sensitivity) |
|---|---|---|
| prose pipeline operating point | sens **0.733** @ flag rate **0.341** | 0.767 @ 0.375 |
| zero-param head: AUROC | **0.949 (95% CI 0.928–0.967)** | 0.949 (0.928–0.968) |
| sensitivity Δ at matched flag rate | **+0.000 (95% CI −0.029 to +0.030)** | +0.034 (−0.009 to +0.065) |

→ **Exact parity / non-inferiority.** A 0.95M-parameter head matches the full 14-billion-parameter decoder + external GPT-5 screener on triage. We do **not** claim superiority (CI brackets zero on both screeners).

**6b. Mechanism — decomposition of the misses.**
| | GPT-5 | Claude |
|---|---|---|
| urgent misses | **55** | 48 |
| decoding | **40 (73%)** | 34 (71%) |
| perception | 10 | 10 |
| reasoning | 5 | 4 |
| decoding reports naming **none of the nine reference findings** | **38/40** | 34/34 |
| median head score on the missed finding | **0.93** | 0.93 |

Decoding-miss findings (GPT-5): **calvarial fracture 9, iph 8, ich 8, sdh 5, mass effect 5, sah 3, edh 2** — the neurosurgical set.

**6c. The 34–40 reports are genuine, not artifacts.**
- 0 empty, 0 truncated, 0 errored. Mean length **139 chars vs 193** for all reports (shorter, substantive).
- Majority are **explicit false-normals** — verbatim *"Study is unremarkable."* / "no acute intracranial abnormality"; the rest name other (often **chronic**, e.g. encephalomalacia) findings while omitting the acute one.
- **Not a blanket default:** normal-reading rate is **23% on urgent vs 96% on non-urgent** — selective false-normalcy on exactly the studies the head flags.

**6d. The head is a good triager per finding (CQ500 AUROC).**
calvarial fracture **0.936**, ich 0.945, iph 0.940, sdh 0.963, sah 0.930, mass effect 0.954. (Fracture behaves well here — the in-house fracture problem is a separate input/label issue, §II.)

**6e. Robustness.**
- **Screener faithfulness:** GPT-5 (authors' model) gives the same story (73% decoding); Claude sensitivity 71%. Acuity agreement GPT-vs-Claude 96.6%.
- **Judge:** κ 0.97 (GPT vs Claude), κ ≥ 0.92 (rule-based). Human 100-report sheet available.
- **Generation determinism:** greedy beam search, **one study per forward pass (batch 1)**; determinism rerun in flight.
- **Calibration:** pooled **ECE 0.251** — the head **discriminates** well but is not calibrated externally ⇒ say "high **score**", not "high probability."
- **Coverage:** standard ASNR critical list **17/18** (gap: cerebral venous sinus thrombosis); **recompute vs their Supp. Fig. 2d** (list needed).
- **Indication ablation (PENDING):** Path-B rerun with "head trauma" and "headache" on all 472 + determinism rerun. Prespecified: *persist* → confound excluded; *resolve* → prose is prompt-context-dependent while the head is not (still task-fit); interpretation written before results.

### 7. Caveats for the text
Single public dataset; 44% vs 13% prevalence; external calibration poor (discrimination transfers, calibration doesn't); screener substitution disclosed and resolved by the GPT-5 re-run; mechanism characterized as false-normal (not truncation).

### 8. Structure (agreed 6)
1) Summary + two concerns. 2) Task fit (triage = discrete decision over a fixed list). 3) Missing baseline (AUROC 0.949; exact parity). 4) Mechanism (40/55 false-normal; 38/40 name none of nine; median 0.93; GPT-5-stable). 5) Indication ablation (robustness). 6) Closing: match readout to task + honest concession (prose helps for out-of-ontology / incidental / laterality-size / synthesis).

---

## PART II — STANDALONE (neuroradiology/neurosurgery)

**Thesis:** the diagnostic head generalizes to an external institution, but performance is governed by **deployment** (input series/recon selection), and a reproducible offline pipeline is needed at scale; a structured calibrated readout rendered from the head is an alternative to free-text prose.

**Data:** in-house de-identified head CTs (RADAR/Project91), 490 primary axial-brain CTs, **343 paired with radiologist reports**. Three token-aligned layers: Path-A 82-dx; TotalSegmentator 16 volumes; report-derived 17 findings (negation-mined).

**Results:**
- **External validation:** mean AUROC **0.82** across 11 well-powered findings (hydrocephalus 0.96, ivh 0.93, iph 0.92, mass effect 0.86, sah 0.83, any-ich 0.79, acute infarct 0.79, …) vs in-domain 0.925 → a ~0.10 domain-shift gap.
- **Input-conditioned perception:** fracture AUROC 0.14 (soft-tissue) → 0.28 (multi-series/bone-kernel); per-case 0.01→0.80. **Still below chance — NOT resolved** (labels/crosswalk also implicated); input selection is part, not all, of the story.
- **Rendered readout vs actual report:** macro-F1 **0.44** at a naive 0.5 threshold (over-calls) → the per-finding **operating-point dial** matters.
- **Contributions:** M1 offline/at-scale LSF pipeline; M2 multi-slice DICOM→NIfTI correctness; M3 multi-series/bone-kernel routing; M4 report-mined negatives; M5 crosswalk; M6 render-from-head; M7 anatomy concordance (pending, zero-GPU).

---

## PART III — FIGURE BRIEF (for constructing the ideal MA figure)

One composite figure (MA allows 1–2). Proposed panels and the exact data each needs:

- **(a) Architecture / the gap.** Schematic: frozen 3D encoder → **Path A** (0.95M attention-MLP head → calibrated 82-dx) and **Path B** (14B decoder → prose → GPT-5 screener → triage). Annotate "the two paths never communicate." Data: none (schematic); label the parameter asymmetry.
- **(b) Missing baseline — parity.** Sensitivity vs flag-rate **curve** for the zero-parameter head score, with the prose pipeline plotted as a **single point**; annotate **AUROC 0.949 [0.928–0.967]** and **Δsens +0.000 [−0.029, +0.030]**. Data: `outputs/reviewer_suite/A2_sens_vs_flagrate.csv` (regenerate on GPT-5 screener) + the prose point (0.733 @ 0.341).
- **(c) Mechanism — decomposition + false-normal.** Stacked bar of the 55 misses → **40 decoding / 10 perception / 5 reasoning**; callout "**38/40 name none of the nine reference findings; median head score 0.93**." Optionally a strip/swarm of head scores on the missed finding for the 40 decoding cases (all > 0.5, clustered near 0.9). Data: `outputs/reviewer_suite/decoding_miss_reports.json` + the GPT-primary decomposition.
- **(d, optional) Robustness panel.** Small multiples: GPT-5 vs Claude screener (same decomposition), judge κ 0.97, and the indication-ablation result (misses persisting under head-trauma/headache) once it lands.

Design notes: keep it readable at single-column; semantic color for decoding (critical) vs perception/reasoning; the head's confident-but-silent swarm in (c) is the emotional core — give it room. The ideal is (a)+(b)+(c) as a 3-panel Figure 1, with (d) as Extended Data.

---

## Scripts (provenance)
`reviewer_suite.py` (A0–A5), `reviewer_ci2.py` (bootstrap/held-out), `gpt_cq500.py` (GPT-5 screener+judge), `gpt_primary.py` (GPT-5-primary recompute), `judge_validation.py` (rule-based + human sheet), `followup.py` (reconcile, false-normal characterization, fracture AUROC), `path_b_indication.py` (ablation). Repo: github.com/Jonah-Keller/neurovfm-matters-arising.
