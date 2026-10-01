# Follow-up round 3

Agreed on all of it. Here's what's done and what's running.

## Substantive

**1. GPT-5 is now the primary analysis — recomputed, and it's cleaner.** Rebuilt the headline on the faithful pipeline (NeuroVFM-LLaVA + GPT-5 screener + GPT-5 mention judge); Claude moves to a sensitivity analysis.

| metric | **GPT-5 (primary)** | Claude (sensitivity) |
|---|---|---|
| urgent / missed | 206 / **55** | 206 / 48 |
| decoding | **40 (73%)** | 34 (71%) |
| perception / reasoning | 10 / 5 | 10 / 4 |
| decoding reports naming none of the 9 reference findings | **38/40** | 34/34 |
| prose operating point | sens 0.733 @ flag 0.341 | 0.767 @ 0.375 |
| zero-param AUROC | **0.949 [0.928, 0.967]** | 0.949 [0.928, 0.968] |
| Δ sensitivity at matched flag rate | **+0.000 [−0.029, +0.030]** | +0.034 [−0.009, +0.065] |

On the faithful pipeline the baseline result is **exact parity** (Δ = 0.000, CI symmetric about zero) — the cleanest possible non-inferiority statement. Decoding is 73%, median head score on the missed finding 0.93, and calvarial fracture is now the single most common decoding miss (9 of 40). All main-text numbers will be GPT-5; Claude in a sensitivity row.

**2. Indication ablation + stability — running now, interpretations prespecified.** CQ500 was still in the project-space cache, so no re-acquisition was needed. Three jobs are live:
- Path-B on **all 472** studies with **"head trauma"** (matches CQ500's emergency source) and, separately, **"headache"** (neutral) — so a leading indication can't be blamed, and false positives on non-urgent studies are measured.
- A **determinism rerun** of the 40 decoding misses (second generation pass) to diff against the cache.

**Prespecified interpretations (to go in Methods before results):**
- *If the decoding misses persist under both indications* → the no-indication confound is excluded; the false-normal mechanism stands.
- *If many resolve under an indication* → the generative readout's sensitivity is **prompt-context-dependent while the head's is not** — which is itself the task-fit argument, not a refutation.
- *Determinism:* the released pipeline generates **one study per forward pass** (batch size 1) with greedy beam search; if the rerun is byte-identical, determinism holds at the deployed batch size. We will not assert cross-batch-size invariance beyond how the model is actually run.

## Small

**3. Matched-flag-rate threshold needs no labels — agreed, and it's the cleaner justification.** The threshold is chosen purely from the score distribution (flag the same fraction the pipeline flags), using no labels, so the in-sample comparison carries no optimism bias. We'll state this in Methods and **drop the 5-fold entirely**.

**4. Both preprocessors present the same windows — confirmed.** `load_vlm` instantiates the **same `StudyPreprocessor`** as the encoder path; CT studies are tokenized into **all three windows (brain/blood/bone)** with no series cap. So the decoder *saw* the bone window and still produced false-normals on 9 calvarial fractures — this strengthens the mechanism rather than confounding it. We'll state it explicitly.

**5. Coverage against their exact list — need Supplementary Fig. 2d.** I computed 17/18 against a standard ASNR list; to make the denominator undisputable I'll recompute against their Supp. Fig. 2d consensus list. **Please send that list (or the panel)** and I'll regenerate the number.

**6. In-house fracture is NOT called resolved.** Point taken — bone-kernel moved it 0.14 → 0.28, still below chance, so something in the labels or crosswalk is also wrong. The standalone will describe input selection as *part* of the story and flag the residual as unresolved. It does not touch the MA.

**7. Wording and denominators — fixed.** "named **none of the nine reference findings**" (13 of them name other, non-reference findings). Single denominator **472** throughout (consensus-joined); the 473 was one extra study with a judge record but no consensus row, now dropped everywhere.

**8. Parameter count — corrected.** The head is **~0.95M parameters** (an attention-pooled gated-MLP, 768→384→82 — not purely linear; you were right). The comparison reads "a ~0.95M-parameter head versus a 14-billion-parameter decoder plus an external API call" (GPT-5's parameter count isn't public).

## Your next step
**Go ahead and restructure now.** The GPT-5 headline numbers are final and in the table above; the ablation and the exact-coverage number are the only tokens left to fill, and both are in flight. Build the mechanism paragraph as false-normal (38/40 naming none of the nine reference findings; median head score 0.93), the baseline as exact parity, and leave two numbered slots for the ablation and the Supp-2d coverage.
