#!/usr/bin/env python3
"""
Phase 1 — disagreement audit (no training).

Runs entirely on CACHED inference outputs so it is testable without a GPU. Two arms:
  * Arm A = Path B (findings LLM) -> GPT-5 screener -> triage acuity  (cached).
  * Arm B = threshold Path A (diagnostic head) probabilities.          (cached probs.)

Primary output: among Arm A false negatives (ground-truth urgent, Arm A not urgent), the
distribution of Path A's probability on the TRUE diagnosis. Shifted high => encoder saw it,
prose lost it (supports hypothesis). Flat/low vs. a true-negative null => perception failure.

--------------------------------------------------------------------------------------------
Cache formats (produce these from a GPU job with src/wrappers.py; see docs/RUNNING.md):

  path_a_probs.jsonl   one JSON object per study:
      {"study": "CQ500-CT-123", "probs": {"intracranial_hemorrhage": 0.94, ...82 labels...}}

  path_b_triage.jsonl  one JSON object per study:
      {"study": "CQ500-CT-123", "findings": "...", "acuity": "urgent"}
      # `acuity` is parsed from interpret_findings() output; if absent, "triage_text" is
      # parsed with parse_acuity(). acuity in {unremarkable, routine, urgent}.

  consensus CSV        from data/reads_parser.py (per-study 0/1 consensus finding columns).
--------------------------------------------------------------------------------------------
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_jsonl(path: Path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


# Keywords that would appear in free-text findings if the prose MENTIONED a finding. Used to
# operationalise "the report was silent about it" (the paper's actual failure mode). Lowercased
# substring/word match. Deliberately generous on the mention side (a mention counts even if
# vague) so "silent" is the conservative, hard-to-fake condition.
FINDING_KEYWORDS = {
    "ich": ["hemorrhage", "haemorrhage", "hemorrhagic", "bleed", "hematoma", "haematoma"],
    "iph": ["intraparenchymal", "intracerebral", "parenchymal hemorrhage", "parenchymal haemorrhage"],
    "ivh": ["intraventricular"],
    "edh": ["epidural", "extradural"],
    "sah": ["subarachnoid"],
    "sdh": ["subdural"],
    "calvarialfracture": ["fracture"],
    "otherfracture": ["fracture"],
    "masseffect": ["mass effect", "effacement", "compression", "herniation"],
    "midlineshift": ["midline shift", "midline", "shift of"],
}


def prose_mentions(text: str, finding: str) -> bool:
    """True if the findings text plausibly mentions `finding` (see FINDING_KEYWORDS)."""
    t = (text or "").lower()
    return any(k in t for k in FINDING_KEYWORDS.get(finding, []))


def parse_acuity(text: str) -> str:
    """
    Extract acuity from an interpret_findings() output. Urgent wins ties.

    The shipped triage prompt (neurovfm/pipelines/resources/triage_acuity_prompt.txt) emits
    triage_level in {Urgent, Routine, Normal} (NOT 'unremarkable' — that's the Fig-4 paper
    wording). We accept both 'normal' and 'unremarkable' and normalise to 'unremarkable' so
    the rest of the harness has one vocabulary. Only 'urgent' drives an Arm-A urgent decision.
    """
    t = text.lower()
    if re.search(r"\burgent\b", t):
        return "urgent"
    if re.search(r"\broutine\b", t):
        return "routine"
    if re.search(r"\b(normal|unremarkable)\b", t):
        return "unremarkable"
    return "unknown"


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------
def build_ground_truth(consensus: pd.DataFrame, crosswalk: dict,
                       study_col: str = "name") -> pd.DataFrame:
    """
    From per-study consensus findings, compute `gt_urgent` (any urgent finding positive) and
    keep the per-finding GT columns for the FN-true-dx lookup.
    """
    urgent_findings = config.urgent_cq500_findings(crosswalk)
    present = [f for f in urgent_findings if f in consensus.columns]
    missing = sorted(set(urgent_findings) - set(present))
    if missing:
        # Not fatal, but the caller should know the cohort lacks a urgent finding column.
        print(f"[phase1] WARNING: urgent finding columns absent from consensus: {missing}",
              file=sys.stderr)
    gt = consensus[[study_col] + present].copy()
    gt["gt_urgent"] = (gt[present].sum(axis=1) > 0).astype(int)
    return gt


# ---------------------------------------------------------------------------
# Arm decisions
# ---------------------------------------------------------------------------
def arm_b_decision(probs: dict[str, float], urgent_labels: list[str],
                   threshold: float) -> tuple[int, float]:
    """Arm B: urgent iff max Path-A prob over the urgent label union >= threshold."""
    vals = [probs.get(lab, 0.0) for lab in urgent_labels]
    mx = max(vals) if vals else 0.0
    return int(mx >= threshold), mx


def arm_a_decision(acuity: str) -> int:
    """Arm A: urgent iff the triage acuity is 'urgent'."""
    return int(acuity == "urgent")


# ---------------------------------------------------------------------------
# The primary analysis
# ---------------------------------------------------------------------------
def path_a_prob_on_finding(probs: dict[str, float], finding: str, crosswalk: dict) -> float | None:
    """
    Path A's probability that it 'saw' a given CQ500 finding = MAX prob over the crosswalk's
    candidate NeuroVFM labels (the documented ambiguous_combine_rule). None if no mapping.
    """
    cands = config.candidate_labels_for(finding, crosswalk)
    if not cands:
        return None
    return max(probs.get(lab, 0.0) for lab in cands)


def fn_true_dx_distribution(gt: pd.DataFrame, probs_by_study: dict[str, dict],
                            arm_a_by_study: dict[str, int], crosswalk: dict,
                            urgent_labels: list[str], threshold: float,
                            study_col: str = "name",
                            findings_by_study: dict[str, str] | None = None) -> dict:
    """
    Core Phase-1 computation. Returns:
      fn_true_dx:  [{study, finding, prob, prose_silent}]  Path A prob on each TRUE urgent
                   finding in an Arm-A false-negative study. `prose_silent` = the generated
                   findings text did NOT mention this finding (the paper's failure mode).
      tn_null:     [{study, finding, prob}]  the SAME labels' Path A prob in studies that are
                   ground-truth NEGATIVE for that finding (the perception-failure null).
      per_study:   decisions table for auditing.
    """
    urgent_findings = [f for f in config.urgent_cq500_findings(crosswalk) if f in gt.columns]
    findings_by_study = findings_by_study or {}
    fn_true_dx, tn_null, rows = [], [], []

    for _, r in gt.iterrows():
        study = r[study_col]
        probs = probs_by_study.get(study)
        if probs is None:
            continue
        a = arm_a_by_study.get(study)
        if a is None:
            continue
        b, b_max = arm_b_decision(probs, urgent_labels, threshold)
        gt_urgent = int(r["gt_urgent"])
        is_fn_A = gt_urgent == 1 and a == 0            # Arm A false negative (the target cell)
        text = findings_by_study.get(study, "")
        rows.append({"study": study, "gt_urgent": gt_urgent, "arm_a": a, "arm_b": b,
                     "arm_b_max_prob": b_max, "arm_a_false_neg": int(is_fn_A)})
        for finding in urgent_findings:
            p = path_a_prob_on_finding(probs, finding, crosswalk)
            if p is None:
                continue
            if int(r[finding]) == 1 and is_fn_A:
                silent = not prose_mentions(text, finding)
                fn_true_dx.append({"study": study, "finding": finding, "prob": p,
                                   "prose_silent": silent})
            elif int(r[finding]) == 0:
                tn_null.append({"study": study, "finding": finding, "prob": p})

    return {"fn_true_dx": fn_true_dx, "tn_null": tn_null,
            "per_study": pd.DataFrame(rows)}


def separation_auroc(fn_probs: list[float], tn_probs: list[float]) -> float | None:
    """
    AUROC of 'Path A prob separates FN-true-dx (label 1) from TN-null (label 0)'.
    ~1.0 => the head is confident exactly where the prose was silent (SUPPORTS hypothesis).
    ~0.5 => the head is no more confident on missed findings than on true negatives (REFUTES).
    """
    if not fn_probs or not tn_probs:
        return None
    try:
        from sklearn.metrics import roc_auc_score
    except ImportError:
        return None
    y = [1] * len(fn_probs) + [0] * len(tn_probs)
    s = list(fn_probs) + list(tn_probs)
    return float(roc_auc_score(y, s))


def differential_audit(consensus: pd.DataFrame, probs_by_study: dict[str, dict],
                       findings_by_study: dict[str, str], crosswalk: dict,
                       confident_thr: float = 0.5, study_col: str = "name") -> pd.DataFrame:
    """
    The audit across the FULL available differential — every CQ500 label, urgent AND structural,
    not just the triage-urgent set (that breadth IS the thesis). Per finding, among GT-positive
    studies: how often was the prose SILENT about it, and when silent, was the head confident?

    CEILING (state it, don't hide it): CQ500 labels only 14 of NeuroVFM's 82 diagnoses, so only
    these 14 axes are testable on public data; the other 68 are not (no public CT set labels them
    AND carries reports). `head_scoreable=False` marks CQ500 labels with no diagnostic-head
    mapping (laterality -> Phase 2; chronicbleed is a modifier), i.e. audited-but-not-head-scored.
    """
    rows = []
    for finding, spec in crosswalk["findings"].items():
        if finding not in consensus.columns:
            continue
        cands = spec.get("neurovfm_labels", [])
        head_scoreable = bool(cands)
        pos = consensus[consensus[finding] == 1]
        n_pos = len(pos)
        mentioned = silent = silent_conf = 0
        silent_probs = []
        for _, r in pos.iterrows():
            st = r[study_col]
            probs = probs_by_study.get(st)
            text = findings_by_study.get(st, "")
            if prose_mentions(text, finding):
                mentioned += 1
            else:
                silent += 1
                if head_scoreable and probs is not None:
                    p = path_a_prob_on_finding(probs, finding, crosswalk)
                    if p is not None:
                        silent_probs.append(p)
                        silent_conf += int(p >= confident_thr)
        rows.append({
            "finding": finding, "urgent": bool(spec.get("urgent")),
            "head_scoreable": head_scoreable, "n_gt_pos": n_pos,
            "prose_mentioned": mentioned,
            "prose_coverage": round(mentioned / n_pos, 3) if n_pos else None,
            "n_prose_silent": silent,
            "n_silent_head_confident": silent_conf,   # the key cell, per finding
            "silent_head_median_prob": (round(float(np.median(silent_probs)), 3)
                                        if silent_probs else None),
        })
    return pd.DataFrame(rows).sort_values(["urgent", "n_gt_pos"], ascending=[False, False])


def separation_auroc_ci(fn_probs: list[float], tn_probs: list[float],
                        n_boot: int = 10000, seed: int = 0) -> dict | None:
    """
    Point separation AUROC + percentile bootstrap CI (resampling BOTH groups). This is the
    uncertainty on the headline claim. Well-separated + CI above 0.5 => supports hypothesis;
    CI spanning 0.5 => inconclusive/refuted.
    """
    point = separation_auroc(fn_probs, tn_probs)
    if point is None:
        return None
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(seed)
    fn, tn = np.array(fn_probs), np.array(tn_probs)
    boots = []
    for _ in range(n_boot):
        f = fn[rng.integers(0, len(fn), len(fn))]
        t = tn[rng.integers(0, len(tn), len(tn))]
        y = np.r_[np.ones(len(f)), np.zeros(len(t))]
        boots.append(roc_auc_score(y, np.r_[f, t]))
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return {"auroc": round(float(point), 4), "ci_lo": round(float(lo), 4),
            "ci_hi": round(float(hi), 4)}


def summarize(result: dict) -> dict:
    """Headline numbers: arm sensitivities, disagreement, FN-true-dx separation + prose-silent."""
    per = result["per_study"]
    fn = result["fn_true_dx"]
    fn_probs = [d["prob"] for d in fn]
    tn_probs = [d["prob"] for d in result["tn_null"]]
    # The KEY cell: false negatives where the prose was SILENT about the true finding.
    silent = [d for d in fn if d.get("prose_silent")]
    silent_probs = [d["prob"] for d in silent]
    pos = per[per["gt_urgent"] == 1]
    out = {
        "n_studies": len(per),
        "n_gt_urgent": int((per["gt_urgent"] == 1).sum()),
        "arm_a_sensitivity": float((pos["arm_a"] == 1).mean()) if len(pos) else None,
        "arm_b_sensitivity": float((pos["arm_b"] == 1).mean()) if len(pos) else None,
        "n_arm_a_false_neg": int(per["arm_a_false_neg"].sum()),
        "disagreement_rate": float((per["arm_a"] != per["arm_b"]).mean()) if len(per) else None,
        "n_fn_true_dx_points": len(fn_probs),
        "fn_true_dx_median_prob": float(np.median(fn_probs)) if fn_probs else None,
        "tn_null_median_prob": float(np.median(tn_probs)) if tn_probs else None,
        "separation_all": separation_auroc_ci(fn_probs, tn_probs),
        # --- prose-silent (the sharpened test): encoder saw it, prose was silent about it ---
        "n_fn_prose_silent": len(silent),
        "frac_fn_prose_silent": (len(silent) / len(fn)) if fn else None,
        "silent_median_prob": float(np.median(silent_probs)) if silent_probs else None,
        "separation_prose_silent": separation_auroc_ci(silent_probs, tn_probs),
    }
    return out


def plot_distributions(result: dict, out_png: Path) -> None:
    """Overlay FN-true-dx vs TN-null probability histograms."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fn = [d["prob"] for d in result["fn_true_dx"]]
    tn = [d["prob"] for d in result["tn_null"]]
    fig, ax = plt.subplots(figsize=(6, 4))
    bins = [i / 20 for i in range(21)]
    if tn:
        ax.hist(tn, bins=bins, density=True, alpha=0.5, label=f"true-negative null (n={len(tn)})")
    if fn:
        ax.hist(fn, bins=bins, density=True, alpha=0.6,
                label=f"Arm-A false-neg, true dx (n={len(fn)})")
    ax.set_xlabel("Path A probability on the finding")
    ax.set_ylabel("density")
    ax.set_title("Phase 1: did the encoder see what the prose missed?")
    ax.legend()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    print(f"[phase1] wrote {out_png}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def run(consensus_csv: Path, path_a_jsonl: Path, path_b_jsonl: Path,
        out_dir: Path, threshold: float, study_col: str = "name") -> dict:
    crosswalk = config.load_crosswalk()
    urgent_labels = config.urgent_neurovfm_labels(crosswalk)

    consensus = pd.read_csv(consensus_csv)
    gt = build_ground_truth(consensus, crosswalk, study_col=study_col)

    probs_by_study = {r["study"]: r["probs"] for r in load_jsonl(path_a_jsonl)}
    arm_a_by_study, findings_by_study = {}, {}
    for r in load_jsonl(path_b_jsonl):
        acuity = r.get("acuity") or parse_acuity(r.get("triage_text", r.get("findings", "")))
        arm_a_by_study[r["study"]] = arm_a_decision(acuity)
        findings_by_study[r["study"]] = r.get("findings", "")

    result = fn_true_dx_distribution(gt, probs_by_study, arm_a_by_study, crosswalk,
                                     urgent_labels, threshold, study_col=study_col,
                                     findings_by_study=findings_by_study)
    summary = summarize(result)

    # The full-differential audit (all 14 CQ500 labels, urgent + structural).
    diff = differential_audit(consensus, probs_by_study, findings_by_study, crosswalk,
                              confident_thr=threshold, study_col=study_col)

    out_dir.mkdir(parents=True, exist_ok=True)
    diff.to_csv(out_dir / "phase1_differential_audit.csv", index=False)
    result["per_study"].to_csv(out_dir / "phase1_per_study.csv", index=False)
    pd.DataFrame(result["fn_true_dx"]).to_csv(out_dir / "phase1_fn_true_dx.csv", index=False)
    with open(out_dir / "phase1_summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    plot_distributions(result, out_dir / "phase1_fn_prob_distribution.png")
    print(json.dumps(summary, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase 1 disagreement audit (cached inputs).")
    ap.add_argument("--consensus", required=True, type=Path, help="reads_parser consensus CSV")
    ap.add_argument("--path-a", required=True, type=Path, help="path_a_probs.jsonl")
    ap.add_argument("--path-b", required=True, type=Path, help="path_b_triage.jsonl")
    ap.add_argument("--out", type=Path, default=Path("outputs/phase1"), help="output dir")
    ap.add_argument("--threshold", type=float, default=config.ARM_B_THRESHOLD)
    ap.add_argument("--study-col", default="name")
    args = ap.parse_args(argv)
    run(args.consensus, args.path_a, args.path_b, args.out, args.threshold, args.study_col)
    return 0


if __name__ == "__main__":
    sys.exit(main())
