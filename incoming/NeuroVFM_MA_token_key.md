# NeuroVFM Matters Arising token key (round 5)

Do not send the draft to Dr. Hollon until ABLATION_RESULT is filled. Aim to send within one to two weeks; the original paper was published July 10.

## New analyses needed (matched-threshold definitions)
| Token | Definition |
|---|---|
| MATCHED_THRESHOLD | Classifier threshold that flags 34.1% of studies (GPT-5 pipeline flag rate) |
| BOTH_CAUGHT, CLASSIFIER_ONLY, REPORT_ONLY, NEITHER | 2×2 over the 206 urgent studies at the matched threshold. CLASSIFIER_ONLY should equal REPORT_ONLY (equal sensitivity). BOTH + REPORT_ONLY = 151, NEITHER + CLASSIFIER_ONLY = 55 |
| REASONING_N | Report misses whose report named ≥1 of the study's positive critical findings |
| DECODING_N | Remaining report misses flagged by the classifier at the matched threshold, report naming none of the positive critical findings |
| PERCEPTION_N | Remaining report misses not flagged by the classifier. REASONING_N + DECODING_N + PERCEPTION_N = 55 |
| CLAUDE_DECOMPOSITION | Same decomposition with Claude as screener |
| ED1_BY_FINDING | Decoding misses (primary definition) by critical finding |
| URGENCY_SENSITIVITY_RESULT, ED2_URGENCY_SUMMARY | Rerun excluding studies whose only critical finding is calvarial fracture: sensitivity difference with CI and decomposition |
| ABLATION_RESULT, ED2_ABLATION_SUMMARY | Indication ablation ("head trauma", "headache") |
| DETERMINISM_RESULT | Regeneration of decoding misses |
| THEIR_ED9D_INDICATION_EFFECT | What the authors' own Extended Data Fig. 9d shows when the indication is withheld, e.g. "only a modest drop in three-tier acuity accuracy (from X to Y)". Read their panel and quote the numbers exactly. If it shows a large drop, tell me, because the paragraph would need rewriting. |
| COVERAGE_SUPP2D | Coverage against their Supplementary Fig. 2d list (keeps ref. 6 cited in Methods) |

## Text
| Token | Note |
|---|---|
| FIG1A_FINDING, FIG1A_SCORE, FIG1A_REPORT_TEXT | Panel a case |
| ED3_N_CASES, ED3_CASE_DESCRIPTIONS | Example cases |

## Administrative
CLAUDE_MODEL_VERSION, SOFTWARE_VERSIONS, FUNDING_STATEMENT (or delete), DATE_SENT_TO_HOLLON, WORD_COUNT, cover letter date.

## Reference checks
- Ref. 8 (Manrai, *Nature* 655, 1138–1139, 2026) is taken from the reference list of the Beaulieu-Jones and Nemati Matters Arising. Confirm it on the publisher site.
- Ref. 8 previously Kim et al. has been removed with the EHR point.
- Dr. Hollon is listed as the corresponding author ("Correspondence to Todd Hollon") in the original article.
