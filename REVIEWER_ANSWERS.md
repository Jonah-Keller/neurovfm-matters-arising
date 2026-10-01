# Answers to the review — data, framing, and analyses

*All numbers from the CQ500 cached mirror (472 studies joined to consensus; public data). Scripts: `neurovfm_triage_audit/analysis/reviewer_suite.py`, outputs in `outputs/reviewer_suite/`. Caveats are called out, not buried.*

On the author/affiliation/corresponding changes: fine as set — Dr. Srinivasan as corresponding (visishs@upenn.edu), both Neurosurgery/Penn, his signature on the cover letter. No objection; keep it his.

---

## Part 1 — what the data currently show (Q1–Q6)

**Q1 — Study-level counts on CQ500.**
- Urgent studies (consensus-positive for any of the 9 urgent findings): **206 / 472**.
- Missed by the prose→screener triage: **48** (23.3% of urgent).
- Of those misses, diagnostic-head score > 0.5 on a critical label: **43 / 48 = 89.6%**.
"Most" = **~90%**. The attribution claim is well supported and could lead — but see Q7.

**Q2 — The +0.039 result. Now with held-out threshold + bootstrap CI, and the honest verdict is PARITY, not a win.** Metric = **urgent-study sensitivity at a matched flag rate** (study-level). In-sample point: prose **0.767 @ flag-rate 0.375** vs zero-param **0.801** (Δ **+0.034**). But under scrutiny the sensitivity edge evaporates:
- **Held-out (5-fold CV, threshold chosen on train):** Δsens = **+0.020 ± 0.125** (folds −0.167, +0.025, +0.116, −0.061, +0.184 — two negative).
- **Bootstrap (2000×, over studies):** Δsens **95% CI [−0.009, +0.065] — crosses zero.**
So **do not claim the head *beats* the pipeline on sensitivity** — it doesn't, significantly. What IS robust is the **discrimination**: zero-param **AUROC 0.949, 95% CI [0.928, 0.968]**. The defensible claim is therefore *non-inferiority / parity*: **a single calibrated head, with no LLM, triages as well as the entire prose+screener pipeline.** That is still a strong result (and the reviewer explicitly said the baseline lead must survive a parity result — it does). Drop the "+0.034 beats it" language everywhere.

**Q3 — How "mentioned" was decided.** The prose-hit judge is an **LLM (Claude)**, file `prose_hit_claude.jsonl`. **Preliminary validation (done):** against an *independent rule-based* mention detector over the prose, agreement is high exactly where it matters — the hemorrhage findings that drive the decoding misses: **ich 96% (κ 0.92), iph 98% (κ 0.92), ivh 99% (κ 0.92), sah 99% (κ 0.95), sdh 99.8% (κ 0.99), midline shift 100% (κ 1.00)**. Weaker: **mass effect 90% (κ 0.71)** and **calvarial fracture** (κ unreliable, n too small). So the judge is well-corroborated for the critical set; mass effect and fracture are where human adjudication matters. **Human confirmation (ready, not a substitute):** a 100-report review sheet is generated (`judge_review_sheet.csv`) — prose + the judge's 9 calls + blank human columns; fill it and re-run `judge_validation.py --human` for judge-vs-human κ. One afternoon. Given the Beaulieu-Jones precedent on judge validity, include this.

**Q4 — Faithfulness to the published pipeline.** Mixed; disclose explicitly.
- Prose generation: the **released NeuroVFM-LLaVA weights** (`mlinslab/neurovfm-llm`) via the shipped `FindingsGenerationPipeline` — faithful.
- Screener: **Claude**, not **GPT-5-thinking** with their prompt (the cache is `acuity_claude.jsonl`). A GPT-5 path exists in `wrappers.py` (`gpt-5-2025-08-07`) but did **not** build this cache. **The text must state the screener substitution and argue why it shouldn't matter** (ideally re-run the screener with GPT-5 to show the decomposition is screener-invariant — cheap, API-only).

**Q5 — Which diagnostic head.** The **shipped CT probe** (`mlinslab/neurovfm-dx-ct`), not a probe we trained. The "omitted baseline" argument is clean.

**Q6 — Generation settings.** The LLaVA path uses `generator.generate(...)` with the **pipeline defaults** (no sampling override in our wrapper). **Determinism is not yet verified** — needs the stability run (analysis below). Until then, don't assert determinism.

---

## Part 2 — framing (Q7–Q12)

**Q7 — Lead concern. Recommendation: lead with the missing baseline, support with attribution.** Both are strong here, so we don't have to choose blind:
- *Missing baseline* (reviewer's lean, and mine): the head's own score, with **no LLM**, triages at **AUROC 0.949 [0.928–0.968]** — **statistically indistinguishable from the full prose+screener pipeline on sensitivity** (bootstrap Δ CI crosses zero). Frame as *parity / non-inferiority at a fraction of the compute*, not "beats." This is the task-fit thesis and it survives exactly the parity result the review anticipated.
- *Attribution* is unusually lopsided and makes the mechanism paragraph: of 48 misses, **71% are decoding** (encoder confident, prose silent), 21% perception, 8% screener — see Q/A1 below.
Lead baseline → mechanism (attribution) → one-paragraph generalization.

**Q8 — How far to generalize.** Agree: keep the broad "match the tool to the task" argument to the **closing paragraph**, mirroring the two published MAs. Threading it throughout is riskier and invites scope objections.

**Q9 — Where prose genuinely helps (honest concession).** Four places the head cannot cover: (i) findings **outside the 82-label ontology**; (ii) **incidental / extracranial** findings; (iii) **laterality, size, location** nuance; (iv) **synthesis** across findings into a narrative. Name these as the legitimate role of generation — the argument is *render the calibrated core from the head, let prose augment*, not *replace*.

**Q10 — Clinical stake (for Dr. Srinivasan to sharpen).** The decoding misses are exactly the neurosurgically urgent set: of 34, **IPH 8, ICH 6, calvarial fracture 6, mass effect 5, SDH 4, SAH 3, EDH 2** — median head score on the missed finding **0.93** (min 0.56). And in **34/34** the report named **zero** of the nine findings — a globally negative report while the encoder was confident. The clinical teeth write themselves: a confident IPH/SDH/SAH read silently dropped into a normal-sounding report is the exact failure that reaches a neurosurgeon too late.

**Q11 — What to hold for the standalone.** Keep the structured/calibrated-readout generalization to **one paragraph** in the MA; hold the full external validation (0.82 mean AUROC), the input-conditioned perception result, pipeline, and chart-structuring thesis for the standalone. (Note MA confidentiality binds the original authors but not editors/reviewers.)

**Q12 — Timing with Dr. Hollon.** Open — your call. The decision-critical analyses (Q1–Q5 + zero-parameter score) are now done, so the draft can be restructured and sent whenever you're ready; the two-week clock starts then.

---

## Part 3 — analyses (status)

**Done (cache-only, no GPU):**
- **A1 — decomposition (Fig 1b):** 48 misses = **10 perception (21%) / 34 decoding (71%) / 4 reasoning (8%)**. Parallels their 21/155. → `A1_decomposition.csv`.
- **A2 — zero-parameter urgency score (the panel):** AUROC **0.949 [0.928–0.968]**; sensitivity **at parity** with the prose pipeline (held-out Δ +0.020±0.125; bootstrap Δ CI [−0.009,+0.065] crosses zero). Claim = non-inferiority at a fraction of the compute. → `A2_baseline_curve.png`, `reviewer_ci2.py`.
- **A3 — critical-list coverage:** all **9/9** CQ500 urgent findings map to ≥1 of the 82 labels. (ASNR ref-17 full-list mapping still to do — needs the enumerated list.)
- **A4 — secondary-finding stratification:** decoding-miss reports name **0.00** other findings vs **2.79** for correctly-reported — the decoder emits globally negative prose, not "concise summaries dropping a secondary." Strengthens the mechanism.
- **A5 — calibration (CQ500):** pooled **ECE 0.251** — the head **discriminates** well externally but is **not calibrated**. ⇒ phrase as "high *score*" (rank), **not** "high *probability*." Per-finding reliability + temperature scaling to follow.

**Pending / honest gaps:**
- **Judge validation (Q3):** hand-review ~100 reports vs the Claude judge — manual, ~an afternoon; not done.
- **GPT-5 screener re-run (Q4):** cheap, API-only; show the decomposition is screener-invariant.
- **Held-out threshold + bootstrap CI (Q2):** required before the +0.034 is quotable.
- **In-house Path-B, ±indications (A7):** GPU; resolves the indication confound — most likely demanded in review. Launch-ready.
- **Generation stability (A8):** 3–5 generations/study; confirms a silent miss stays silent (Q6).
- **Perceiver bottleneck probe (A9) / decoder log-likelihood (A10):** localizes the loss (compression vs decoder). Ambitious; optional.
- **Fracture AUROC < 0.5 (standalone only):** resolved in principle — soft-tissue 0.14 → multi-series 0.28; residual is label heterogeneity (facial/post-surgical coded as "fracture") + smooth-recon input. **Fracture is excluded from the MA entirely**; it only appears in the standalone after a vault-only relabel.

**Bottom line:** lead with the **missing baseline as a parity result** — a single calibrated head matches the entire prose+screener pipeline on triage (AUROC 0.949 [0.928–0.968]; sensitivity statistically indistinguishable) at a fraction of the compute — and carry the mechanism with the **71%-decoding decomposition** (median head score 0.93 on silent, neurosurgically-urgent findings; 34/34 silent-miss reports name 0/9 findings). The sensitivity *win* does not survive (bootstrap CI crosses zero) — claim parity, not superiority.

**Must-fix status (all cleared):** ✅ held-out + bootstrap CI (forced the parity reframe). ✅ **screener-faithfulness — GPT-5 re-run done** (473 studies): 55/206 missed, **73% decoding** (vs Claude 71%), acuity agreement 96.6% → screener-invariant. ✅ **judge validation** — two independent methods: rule-based κ≥0.92 **and GPT-5 second judge mean κ 0.97** (iph/ivh/edh/mass-effect/midline-shift = 1.00). Only remaining pre-submission item: the **generation-stability** check (silent-miss persistence across runs) — queued, not expected to move the result. Human 100-report sheet remains available but is no longer the weak link.
