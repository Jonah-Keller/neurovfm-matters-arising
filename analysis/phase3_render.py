#!/usr/bin/env python3
"""
Phase 3 — the report-rendering "dial".

Render a templated findings list FROM Path A's calibrated 82-diagnosis differential (+ the
Phase-2 laterality head), instead of Path B's free-form prose. The key knob is a per-diagnosis
probability THRESHOLD — turning it trades sensitivity for specificity. We then ask the payoff
question: at a sensible operating point, does the dial-rendered report RECOVER the findings
Path B's prose was silent about?

Runs on cached Path-A probs (from build_cache) — GPU-free and testable now.

Outputs:
  phase3_rendered.jsonl        per study: the rendered findings list at the chosen dial
  phase3_dial_sweep.csv        finding-level sensitivity/specificity across thresholds
  phase3_recovery.json         among Arm-A silent misses, how many the dial recovers

TODO: size/location slots from AB-MIL attention maps (needs attention export, later increment).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import config  # noqa: E402
from analysis import phase1_disagreement as p1  # reuse prose_mentions / crosswalk helpers  # noqa: E402

TEMPLATES_PATH = config.REPO_ROOT / "mapping" / "findings_templates.yaml"


def load_templates(path: Path | None = None) -> dict:
    with open(path or TEMPLATES_PATH) as f:
        return yaml.safe_load(f)


def render_findings(probs: dict[str, float], thresholds: dict[str, float],
                    laterality: dict[str, int] | None = None,
                    templates: dict | None = None) -> list[dict]:
    """
    Render the findings list: every label with prob >= its threshold emits its sentence,
    ordered by probability (a proxy for clinical salience). `thresholds['__default__']` is the
    fallback knob (the "dial"). laterality maps label -> 0(left)/1(right) for lateralizable ones.
    """
    templates = templates or load_templates()
    tpl, meta = templates["templates"], templates["meta"]
    side_words = meta["side_words"]
    laterality = laterality or {}
    out = []
    for label, p in sorted(probs.items(), key=lambda kv: -kv[1]):
        thr = thresholds.get(label, thresholds.get("__default__", 0.5))
        if p < thr:
            continue
        spec = tpl.get(label)
        side = ""
        if spec and spec.get("lateralizable") and label in laterality:
            side = {0: side_words["left"], 1: side_words["right"]}.get(laterality[label], "")
        text = (spec["text"] if spec else meta["fallback"])
        text = text.replace("{side}", side).replace(
            "{diagnosis}", label.replace("_", " ").capitalize())
        out.append({"label": label, "prob": round(float(p), 4), "text": text})
    return out


def rendered_positive_findings(rendered: list[dict], crosswalk: dict) -> set[str]:
    """Map the rendered NeuroVFM labels back to CQ500 finding tags (for scoring vs GT/prose)."""
    label_to_findings: dict[str, list[str]] = {}
    for tag, spec in crosswalk["findings"].items():
        for lab in spec.get("neurovfm_labels", []):
            label_to_findings.setdefault(lab, []).append(tag)
    tags = set()
    for r in rendered:
        tags.update(label_to_findings.get(r["label"], []))
    return tags


def dial_sweep(consensus: pd.DataFrame, probs_by_study: dict[str, dict], crosswalk: dict,
               grid: list[float], study_col: str = "name") -> pd.DataFrame:
    """
    Per-CQ500-finding sensitivity/specificity of the dial as the default threshold varies.
    This IS the dial's operating characteristic — the deliverable knob.
    """
    findings = [t for t in crosswalk["findings"]
                if config.candidate_labels_for(t, crosswalk) and t in consensus.columns]
    rows = []
    for thr in grid:
        for finding in findings:
            tp = fp = tn = fn = 0
            for _, r in consensus.iterrows():
                st = r[study_col]
                if st not in probs_by_study:
                    continue
                p = p1.path_a_prob_on_finding(probs_by_study[st], finding, crosswalk)
                if p is None:
                    continue
                pred = int(p >= thr)
                gt = int(r[finding])
                tp += pred and gt; fp += pred and not gt
                tn += (not pred) and (not gt); fn += (not pred) and gt
            sens = tp / (tp + fn) if (tp + fn) else None
            spec = tn / (tn + fp) if (tn + fp) else None
            rows.append({"threshold": thr, "finding": finding, "n_pos": tp + fn,
                         "sensitivity": sens, "specificity": spec, "tp": tp, "fp": fp})
    return pd.DataFrame(rows)


def matched_alarm_comparison(consensus: pd.DataFrame, probs_by_study: dict[str, dict],
                             findings_by_study: dict[str, str], crosswalk: dict,
                             study_col: str = "name") -> dict:
    """
    THE HEADLINE METRIC (redefined). A raw "recovery rate" is an own goal: it rises when the
    dial floods every field, so a useless model scores 100%. Instead we compare prose vs the
    dial AT A MATCHED ALARM BUDGET.

    Alarm = a positive finding assertion (study, finding). We build the full (study x finding)
    grid over every CQ500 label with a head mapping, tag each cell with ground truth, whether
    the PROSE mentioned it, and the head's probability. Then:
      * prose baseline: its alarm count and its sensitivity (true findings it asserted).
      * dial: set ONE threshold so the dial fires the SAME NUMBER of alarms as the prose, and
        measure the dial's sensitivity at that budget.
    Headline = dial_sensitivity - prose_sensitivity at equal alarms. Positive => "at equal
    alarm budget, the differential-rendered report catches more true findings than prose."
    This is the direct quantitative form of "the dial beats the fixed point."

    NOTE: finding-level (not study-level) because the thesis is that the DIFFERENTIAL carries
    breadth prose drops. `findings_by_study` must be REAL Path-B text for this to mean anything;
    with stub text it is only a plumbing check.
    """
    findings = [t for t in crosswalk["findings"]
                if config.candidate_labels_for(t, crosswalk) and t in consensus.columns]
    rec = []
    for _, r in consensus.iterrows():
        st = r[study_col]
        probs = probs_by_study.get(st)
        if probs is None:
            continue
        text = findings_by_study.get(st, "")
        for f in findings:
            p = p1.path_a_prob_on_finding(probs, f, crosswalk)
            if p is None:
                continue
            rec.append({"gt": int(r[f]), "prose": int(p1.prose_mentions(text, f)),
                        "prob": float(p)})
    if not rec:
        return {"note": "no (study,finding) pairs — need cached probs + consensus."}
    df = pd.DataFrame(rec)
    n_true = int((df["gt"] == 1).sum())

    prose_alarms = int(df["prose"].sum())
    prose_tp = int(((df["prose"] == 1) & (df["gt"] == 1)).sum())
    prose_sens = prose_tp / n_true if n_true else None

    # Dial fires its top-`prose_alarms` cells by probability => exactly matched alarm budget.
    order = df.sort_values("prob", ascending=False).reset_index(drop=True)
    k = min(prose_alarms, len(order))
    thr_star = float(order["prob"].iloc[k - 1]) if k > 0 else 1.0
    dial_mask = df["prob"] >= thr_star
    dial_alarms = int(dial_mask.sum())
    dial_tp = int((dial_mask & (df["gt"] == 1)).sum())
    dial_sens = dial_tp / n_true if n_true else None

    return {
        "n_pairs": len(df), "n_true_findings": n_true,
        "prose_alarms": prose_alarms, "prose_alarm_rate": round(prose_alarms / len(df), 4),
        "prose_sensitivity": None if prose_sens is None else round(prose_sens, 4),
        "matched_threshold": round(thr_star, 4), "dial_alarms": dial_alarms,
        "dial_sensitivity": None if dial_sens is None else round(dial_sens, 4),
        # >0 => dial beats prose at equal alarm budget (the headline claim)
        "sensitivity_delta": (None if (dial_sens is None or prose_sens is None)
                              else round(dial_sens - prose_sens, 4)),
    }


def run(consensus_csv: Path, path_a_jsonl: Path, path_b_jsonl: Path | None, out_dir: Path,
        threshold: float, laterality_jsonl: Path | None) -> dict:
    crosswalk = config.load_crosswalk()
    templates = load_templates()
    consensus = pd.read_csv(consensus_csv)
    probs_by_study = {r["study"]: r["probs"]
                      for r in (json.loads(l) for l in open(path_a_jsonl) if l.strip())}
    findings_by_study = {}
    if path_b_jsonl and path_b_jsonl.exists():
        findings_by_study = {r["study"]: r.get("findings", "")
                             for r in (json.loads(l) for l in open(path_b_jsonl) if l.strip())}
    lat_by_study = {}
    if laterality_jsonl and laterality_jsonl.exists():
        lat_by_study = {r["study"]: r.get("laterality", {})
                        for r in (json.loads(l) for l in open(laterality_jsonl) if l.strip())}

    out_dir.mkdir(parents=True, exist_ok=True)
    thresholds = {"__default__": threshold}
    with open(out_dir / "phase3_rendered.jsonl", "w") as f:
        for st, probs in probs_by_study.items():
            rendered = render_findings(probs, thresholds, lat_by_study.get(st), templates)
            f.write(json.dumps({"study": st, "findings": rendered}) + "\n")

    sweep = dial_sweep(consensus, probs_by_study, crosswalk,
                       grid=[round(x, 2) for x in np.arange(0.1, 0.95, 0.1)])
    sweep.to_csv(out_dir / "phase3_dial_sweep.csv", index=False)

    headline = {}
    if findings_by_study:
        headline = matched_alarm_comparison(consensus, probs_by_study, findings_by_study,
                                            crosswalk)
        with open(out_dir / "phase3_matched_alarm.json", "w") as f:
            json.dump(headline, f, indent=2)

    print(f"[phase3] rendered {len(probs_by_study)} studies at dial={threshold}")
    print(f"[phase3] dial sweep -> phase3_dial_sweep.csv "
          f"({sweep['finding'].nunique()} findings x {sweep['threshold'].nunique()} thresholds)")
    if headline:
        print(f"[phase3] MATCHED-ALARM HEADLINE: {json.dumps(headline)}")
    else:
        print("[phase3] (no Path-B findings supplied -> matched-alarm headline skipped)")
    return {"n_studies": len(probs_by_study), "matched_alarm": headline}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase 3 report-rendering dial.")
    ap.add_argument("--consensus", required=True, type=Path)
    ap.add_argument("--path-a", required=True, type=Path, help="path_a_probs.jsonl")
    ap.add_argument("--out", type=Path, default=Path("outputs/phase3"))
    ap.add_argument("--threshold", type=float, default=0.5, help="the dial (default per-dx thr)")
    ap.add_argument("--laterality", type=Path, help="optional laterality.jsonl (Phase 2 head)")
    ap.add_argument("--path-b", type=Path,
                    help="path_b_triage.jsonl (Path-B findings) for the matched-alarm headline")
    args = ap.parse_args(argv)
    run(args.consensus, args.path_a, args.path_b, args.out, args.threshold, args.laterality)
    return 0


if __name__ == "__main__":
    sys.exit(main())
