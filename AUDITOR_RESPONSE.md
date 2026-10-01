# Response to the review

Thanks — this sharpened the paper. The author/affiliation changes are good as set: Dr. Srinivasan corresponding (visishs@upenn.edu), both of us Neurosurgery/Penn, his signature on the cover letter. Keep it his.

Below I answer the data questions first (they decide whether the claims hold), then framing, then the analysis status. Numbers are from the CQ500 cached mirror (472 studies joined to consensus; public data); scripts and outputs are in the repo.

## What the data show (Q1–Q6)

**Q1 — counts.** 206 urgent studies (consensus). The prose→screener pipeline missed **48** (23%). Of those, the diagnostic head scored above threshold on a critical label in **43/48 = 90%**. So "most" is **~90%** — and it's lopsided enough that attribution is a real option, though see Q7.

**Q2 — the sensitivity result, with the honest verdict.** The metric is **urgent-study sensitivity at a matched flag rate** (study level). In-sample the head's zero-parameter score reaches sens 0.801 vs the pipeline's 0.767 — Δ +0.034. **But it does not survive scrutiny:** a 5-fold held-out threshold gives Δ +0.020 ± 0.125 (two folds negative), and a 2000× bootstrap gives a 95% CI of **[−0.009, +0.065] — it crosses zero.** What *is* robust is discrimination: **AUROC 0.949, 95% CI [0.928, 0.968].** So we should **not** claim the head beats the pipeline; we should claim **parity/non-inferiority at a fraction of the compute.** The threshold is swept, not held out, for the in-sample point — the held-out and bootstrap numbers above are the ones to quote.

**Q3 — the mention judge.** It's an LLM (Claude), and it's now validated by two independent methods. Against a rule-based detector, agreement is high where it matters — ich 96% (κ 0.92), iph 98% (0.92), ivh 99% (0.92), sah 99% (0.95), sdh 99.8% (0.99), midline shift 100% (1.00). Against a **GPT-5 second judge** (all 473 studies), inter-rater agreement is near-perfect: **mean κ 0.97** (iph/ivh/edh/mass-effect/midline-shift κ = 1.00; ich 0.93; sah/sdh 0.99). A 100-report human adjudication sheet is also ready. Given the Beaulieu-Jones precedent we report all three — but the judge is clearly not the weak link.

**Q4 — faithfulness.** Prose was generated with the **released NeuroVFM-LLaVA weights** (`mlinslab/neurovfm-llm`) via the shipped pipeline — faithful. The screener in the first cache was **Claude, not GPT-5** — so I re-ran the screener with **GPT-5** on all 473 studies. The conclusion is screener-stable: GPT-5 misses **55/206** urgent studies (vs Claude's 48), of which **73% are decoding** (vs 71%), with **96.6%** acuity agreement between the two screeners. If anything the authors' own screener strengthens the decoding story. This is also true analytically: the decoding misses are reports naming **0 of 9 findings** — an empty report that *no* screener can triage. We'll disclose the original substitution and report the GPT-5 re-run.

**Q5 — which head.** The **shipped CT probe** (`mlinslab/neurovfm-dx-ct`), not one we trained. The omitted-baseline argument is clean.

**Q6 — generation settings.** The LLaVA path runs at the pipeline defaults (no sampling override in our wrapper); determinism is **not yet verified** — the stability run (3–5 generations/study) is the clean way to settle it and is queued. Until then we don't assert determinism.

## Framing (Q7–Q12)

**Q7 — lead.** I agree with you: **lead with the missing baseline, as a parity result.** "A single calibrated head, with no LLM, triages as well as the entire prose+screener pipeline (AUROC 0.949), at a fraction of the compute" carries the task-fit thesis and survives exactly the parity outcome we now have. Then use attribution as the **mechanism**: 71% of the misses are decoding (encoder confident, prose silent), and in 34/34 the report named zero findings while the head's median score on the missed finding was 0.93. We do not claim a sensitivity win.

**Q8 — generalization.** Keep the broad "match the tool to the task" argument to the closing paragraph, mirroring the two published MAs. Threading it throughout invites scope objections.

**Q9 — where prose helps.** Honestly: findings outside the 82-label ontology, incidental/extracranial findings, laterality/size/location nuance, and narrative synthesis. The argument is *render the calibrated core from the head and let prose augment*, not replace.

**Q10 — clinical stake (your teeth to add).** The decoding misses are the neurosurgical set: IPH 8, ICH 6, calvarial fracture 6, mass effect 5, SDH 4, SAH 3, EDH 2 — median head score 0.93, and every one a report that read essentially normal. A confident IPH or SDH silently dropped into a normal-sounding report is the exact failure that reaches us too late.

**Q11 — what to hold.** Keep the structured-readout generalization to one paragraph here; the full external validation, the input-conditioned perception result, the pipeline, and the chart-structuring thesis go in the standalone. (MA confidentiality binds the original authors, not the editors/reviewers.)

**Q12 — timing with Dr. Hollon.** Your call — the decision-critical analyses are done, so the draft can be restructured and sent whenever you're ready.

## Analyses

Done (CQ500, cache-only): decomposition (Fig 1b: 10 perception / 34 decoding / 4 reasoning); zero-parameter urgency score (AUROC 0.949, parity vs prose; `A2_baseline_curve.png`); critical-list coverage 9/9; secondary-finding stratification (decoding-miss reports name 0.00 other findings vs 2.79); calibration (ECE 0.251 pooled → report "high score", not "high probability"); held-out + bootstrap CIs; rule-based judge validation.

Done since the review: GPT-5 screener re-run + GPT-5 second-judge on all 473 studies (κ 0.97; screener-stable at 73% decoding). Still queued: generation-stability (3–5 generations/study) and, for the standalone, Path-B on the in-house cohort ±indications.

On your point about our own reports: yes — we have the **actual radiologist reports** for the in-house cohort, which CQ500 lacks. That lets us score our Path-A-rendered report against the real report for finding accuracy and similarity. That belongs in the **standalone** paper (new cohort, new primary result), not the MA; a first pass shows the rendered readout needs a per-finding operating point (at a naive 0.5 threshold it over-calls, macro-F1 0.44) — i.e. the "dial" matters, which is itself part of the standalone's story.

**Bottom line:** restructure around the baseline-parity lead with the decoding decomposition as mechanism — both now robust (parity CI, κ 0.97 judge, screener-invariant at 73% decoding). The only remaining pre-submission item is the generation-stability check (does a silent miss stay silent across runs); the human judge adjudication is a nice-to-have given the κ 0.97, not a blocker. None of these is likely to move the conclusion.
