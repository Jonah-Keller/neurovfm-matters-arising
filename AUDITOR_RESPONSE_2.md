# Follow-up: blockers resolved

Good catches. Numbers below reconcile everything; one item (the indication ablation) needs CQ500 images we no longer have on disk — see B4.

## Blockers

**1. The two counts — reconciled; adopt the finding-specific definition.** You're exactly right about the cause. Of the 48 misses:
- *any* critical label > 0.5: **43** (this produced the 90%),
- the **specific missed finding** > 0.5: **38** (= 34 decoding + 4 reasoning, which are mentioned-but-not-escalated and also score high),
- **decoding** (prose silent *and* the specific missed finding > 0.5): **34**, perception 10, reasoning 4.

Use the finding-specific definition everywhere and quote **34/48 (71%)**. Drop the 90%.

**2. What the 34 reports actually say — genuine, not artifacts.** I pulled the raw text of all 34 (`decoding_miss_reports.json`):
- **0 are literally empty; 0 are truncated or errored.** Mean length 139 characters vs 193 for all reports — shorter but substantive.
- **21/34 are explicit false-normals** — e.g. verbatim *"Study is unremarkable."* or "no acute intracranial abnormality."
- The other ~13 are non-empty reports that **named other findings — frequently chronic (e.g. "extensive encephalomalacia… ex vacuo dilatation")** — while omitting the acute urgent finding. So the mechanism is *false-normal / wrong-emphasis*, not truncation and not "busy report dropped a secondary" (the secondary analysis already killed that).
- **Decisive against a pipeline artifact:** the decoder does **not** blanket-default to normal. Normal-reading rate is **23% on urgent studies vs 96% on non-urgent** — it correctly calls 77% of urgent studies and correctly calls 96% of non-urgent ones normal. A truncation/empty-output bug or a "defaults to normal" failure would hit both strata; this is selective false-normalcy on exactly the studies the head flags.

So the mechanism paragraph becomes a **false-normal** paragraph, which is the stronger version. Raw text is in the repo for your read.

**3. Same input to both readouts — confirmed.** The cache builder feeds **the same series set** (`cq500_index.series_dirs(study_dir)`) to both paths and pools all diagnostic series per study (matching the paper's "pool all diagnostic series"); AB-MIL aggregation is order-invariant. Each path then applies its own *standard* preprocessor (the released design — encoder preprocessor for the head, VLM preprocessor for the decoder). It is apples-to-apples at the volume level: neither readout saw a series the other didn't.

**4. The indication confound — I agree it's now the key robustness check, and here's the honest status.** The cache was generated with **`clinical_context=""`** (no indication) — so the confound is live. The counter-evidence above is strong (selective 23% false-normal, not a blanket default), but it is not the ablation you want. **The ablation itself is currently blocked:** the CQ500 DICOMs lived on node-local `/scratch` and have been purged, so I can't re-run Path-B with a generic indication without re-downloading CQ500 (public) and a GPU node. I'd propose we do exactly your experiment — re-acquire CQ500, rerun Path-B with `clinical_context="head trauma"` / "acute neurological deficit", and report whether the 34 decoding misses persist. Flagging it as the one outstanding compute item before the mechanism paragraph is final.

## Smaller fixes

**5. Parity language + which CI.** Agreed — I'll write "comparable sensitivity at a matched flag rate (**difference +0.034, 95% CI −0.009 to +0.065**), with AUROC 0.949 (95% CI 0.928–0.968)." The CI to quote is the **bootstrap that re-selects the flag-rate-matched threshold within each resample** (that's how it's computed), not the fixed-threshold one. The 5-fold Δ (+0.020 ± 0.125) goes in Methods only, as you suggest.

**6. The compute claim — now with a number.** Both paths share the encoder, so the honest marginal comparison is: the **diagnostic readout is an attention-pooled linear head (82-way classifier, ~0.06M parameters)** on the shared tokens; the **prose readout is autoregressive generation from a 14-billion-parameter decoder (512 tokens, 4 beams) plus a separate GPT-5 screening call per study.** So the readout that triages adds ~5 orders of magnitude fewer parameters and avoids a second model entirely. I'll phrase it as parameters + "no second (LLM) model and no external API call," and cite ED Fig. 9c's per-100-study template.

**7. Coverage — corrected to the ASNR-list framing.** Against a standard ASNR/ACR neuro critical-findings list, the 82 CT labels cover **17/18 (94%)**. The notable gap is **cerebral venous sinus thrombosis** (no corresponding label); aneurysm is only covered via ruptured-SAH, and empyema only via abscess. This scopes the task-fit claim honestly. *Please confirm against their ref. 17 so we use their exact list* — I used a standard one.

**8. Prevalence.** CQ500 is 44% urgent (206/472) vs 13% in their prospective week — one limitations sentence. I'll add the optional reweighted flag-rate axis to 13% as an Extended Data panel.

**9. Fracture on CQ500 — behaves well, keep it.** CQ500 **calvarial-fracture AUROC = 0.936** (ich 0.945, iph 0.940, sdh 0.963, sah 0.930, mass effect 0.954). So the head handles fracture fine on CQ500; the 6 fracture decoding misses are legitimate. The inverted in-house fracture AUROC (0.14) was an **input-selection artifact** (soft-tissue vs bone-kernel recon) + label heterogeneity — a separate standalone story, not a model failure, and it does not touch the MA.

## Not blockers
Generation stability is **settled by the released config** — greedy beam search (`do_sample=False, num_beams=4`), deterministic, no run-to-run variance. Human adjudication stays optional given the two LLM judges agree at κ 0.97 (rule-based κ≥0.92, GPT-5 κ 0.97); I'll report all three so the judge question disappears.

## Net
Your six-point structure holds. The only thing standing between us and a final mechanism paragraph is the **indication ablation**, which needs CQ500 re-acquired on a GPU node. Everything else is in hand, and the false-normal characterization (item 2) is ready for you to restructure around — raw text is in the repo.
