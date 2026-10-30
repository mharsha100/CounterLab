"""Deterministic evaluation of measured rows. Standard library only.

Every number in a finding comes from here, computed from the sandbox rows.
The model's text appears only as clearly attributed claims and explanations.
This file is copied into replay packages unchanged.
"""

import hashlib
import json
import math

REPORT_VERSION = "open_report_v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256((canonical(value) + "\n").encode()).hexdigest()


def rounded(value, places=6):
    return None if value is None else float(f"{value:.{places}g}")


def stats(values):
    if not values:
        return {"n": 0, "mean": None, "std": None, "min": None, "max": None}
    mean = math.fsum(values) / len(values)
    var = math.fsum((v - mean) ** 2 for v in values) / len(values)
    return {"n": len(values), "mean": rounded(mean), "std": rounded(math.sqrt(var)),
            "min": rounded(min(values)), "max": rounded(max(values))}


def sign_test(positive, negative):
    """Two-sided exact binomial p-value for the sign of paired differences (ties excluded)."""
    n = positive + negative
    if n == 0:
        return None
    k = min(positive, negative)
    tail = math.fsum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return rounded(min(1.0, 2 * tail), 4)


def holds(relation, difference, tolerance):
    if relation == "greater":
        return difference > tolerance
    if relation == "less":
        return difference < -tolerance
    return abs(difference) <= tolerance


def evaluate(plan, run_a, run_b):
    """run_a/run_b: sandbox results for the same harness. Returns the experiment record."""
    conditions = [item["id"] for item in plan["conditions"]]
    metrics = [item["id"] for item in plan["metrics"]]
    seeds = list(plan["seeds"])
    rows_a = {(row["condition"], row["seed"]): row for row in run_a.get("rows", [])}
    rows_b = {(row["condition"], row["seed"]): row for row in run_b.get("rows", [])} if run_b else {}
    errors = [{"condition": key[0], "seed": key[1], "error": row["error"]} for key, row in rows_a.items() if "error" in row]
    complete = run_a.get("status") == "ok" and len(rows_a) == len(conditions) * len(seeds) and not errors
    stable = {}
    for metric in metrics:
        same = bool(rows_b) and all(
            "values" in rows_a.get((c, s), {}) and "values" in rows_b.get((c, s), {})
            and rows_a[(c, s)]["values"][metric] == rows_b[(c, s)]["values"][metric]
            for c in conditions for s in seeds)
        stable[metric] = same
    table = {}
    for metric in metrics:
        table[metric] = {}
        for condition in conditions:
            values = [rows_a[(condition, seed)]["values"][metric] for seed in seeds
                      if "values" in rows_a.get((condition, seed), {})]
            table[metric][condition] = {**stats(values), "per_seed": [rounded(v) for v in values]}
    verdicts = []
    for explanation in plan["explanations"]:
        for item in explanation["expected"]:
            metric, left, right = item["metric"], item["left"], item["right"]
            pairs = [(rows_a[(left, s)]["values"][metric], rows_a[(right, s)]["values"][metric]) for s in seeds
                     if "values" in rows_a.get((left, s), {}) and "values" in rows_a.get((right, s), {})]
            entry = {"explanation": explanation["id"], **item, "seeds_compared": len(pairs)}
            if not complete or not pairs:
                entry.update(status="inconclusive", reason="measurements incomplete")
            elif not stable[metric]:
                entry.update(status="inconclusive", reason="metric did not repeat exactly across the two runs")
            else:
                left_mean = math.fsum(a for a, _ in pairs) / len(pairs)
                right_mean = math.fsum(b for _, b in pairs) / len(pairs)
                difference = left_mean - right_mean
                agree = sum(holds(item["relation"], a - b, item["tolerance"]) for a, b in pairs)
                positive = sum(a > b for a, b in pairs)
                negative = sum(a < b for a, b in pairs)
                entry.update(left_mean=rounded(left_mean), right_mean=rounded(right_mean),
                             difference=rounded(difference), seeds_agreeing=agree,
                             sign_test_p=sign_test(positive, negative),
                             status="held" if holds(item["relation"], difference, item["tolerance"]) else "failed")
            verdicts.append(entry)
    explanations = []
    for explanation in plan["explanations"]:
        own = [v for v in verdicts if v["explanation"] == explanation["id"]]
        if any(v["status"] == "failed" for v in own):
            status = "contradicted"
        elif own and all(v["status"] == "held" for v in own):
            status = "consistent"
        else:
            status = "inconclusive"
        explanations.append({"id": explanation["id"], "statement": explanation["statement"], "status": status,
                             "held": sum(v["status"] == "held" for v in own),
                             "failed": sum(v["status"] == "failed" for v in own),
                             "inconclusive": sum(v["status"] == "inconclusive" for v in own)})
    status_of = {e["id"]: e["status"] for e in explanations}
    consistent = [e["id"] for e in explanations if e["status"] == "consistent"]
    if status_of.get(plan["bet"]) == "consistent" and len(consistent) == 1:
        bet = "held"
    elif status_of.get(plan["bet"]) == "contradicted":
        bet = "failed"
    else:
        bet = "undecided"
    record = {"report_version": REPORT_VERSION, "complete": complete, "errors": errors[:20],
              "reproduced": bool(rows_b) and all(stable.values()), "stable_metrics": stable,
              "measurements": table, "verdicts": verdicts, "explanations": explanations,
              "bet": {"explanation": plan["bet"], "outcome": bet},
              "rows_sha256": digest(run_a.get("rows", [])), "repeat_rows_sha256": digest(run_b.get("rows", [])) if run_b else None}
    record["finding"] = finding(plan, record)
    return record


def fmt(value):
    if value is None:
        return "n/a"
    if value == int(value) and abs(value) < 1e15:
        return f"{int(value):,}"
    if abs(value) >= 1000:
        return f"{value:,.1f}"
    return f"{value:.4g}"


FLIP = {"greater": "less", "less": "greater", "equal": "equal"}


def expectation_text(relation, left, right, tolerance):
    if relation == "equal":
        return f"{left} and {right} equal within ±{fmt(tolerance)}"
    word = "higher" if relation == "greater" else "lower"
    margin = f" by more than {fmt(tolerance)}" if tolerance else ""
    return f"{left} {word} than {right}{margin}"


def finding(plan, record):
    """Plain-language sentences assembled from measured values only."""
    labels = {c["id"]: c["label"] for c in plan["conditions"]}
    metric_labels = {m["id"]: m["label"] for m in plan["metrics"]}
    lines = []
    if not record["complete"]:
        lines.append("The experiment did not complete for every condition and seed, so no expectation is judged.")
    elif not record["reproduced"]:
        unstable = [metric_labels[m] for m, ok in record["stable_metrics"].items() if not ok]
        lines.append("The repeat run did not reproduce every value exactly"
                     + (f" ({', '.join(unstable)})" if unstable else "") + "; those comparisons are not judged.")
    groups = {}
    for verdict in record["verdicts"]:
        if verdict["status"] == "inconclusive":
            continue
        key = (verdict["metric"], frozenset((verdict["left"], verdict["right"])))
        groups.setdefault(key, []).append(verdict)
    for (metric, _), verdicts in groups.items():
        first = verdicts[0]
        left, right = first["left"], first["right"]
        line = (f"{metric_labels[metric]}: {labels[left]} {fmt(first['left_mean'])} vs {labels[right]} "
                f"{fmt(first['right_mean'])} (mean of {first['seeds_compared']} seeds).")
        parts = []
        for verdict in verdicts:
            relation, tolerance = verdict["relation"], verdict["tolerance"]
            if verdict["left"] != left:
                relation = FLIP[relation]
            parts.append(f"{verdict['explanation']} expected {expectation_text(relation, labels[left], labels[right], tolerance)}: "
                         f"{verdict['status']} ({verdict['seeds_agreeing']}/{verdict['seeds_compared']} seeds agree).")
        lines.append(line + " " + " ".join(parts))
    standing = [e["id"] for e in record["explanations"] if e["status"] == "consistent"]
    ruled_out = [e["id"] for e in record["explanations"] if e["status"] == "contradicted"]
    if record["complete"] and record["reproduced"]:
        if standing and ruled_out:
            lines.append(f"Consistent with the measurements: {', '.join(standing)}. Contradicted: {', '.join(ruled_out)}.")
        elif standing:
            lines.append(f"Every explanation that was judged is consistent ({', '.join(standing)}); this experiment does not separate them.")
        elif ruled_out:
            lines.append(f"Every explanation's expectations failed ({', '.join(ruled_out)}); the right explanation is not among them.")
    outcome = record["bet"]["outcome"]
    lines.append(f"Nemotron's committed bet ({record['bet']['explanation']}) "
                 + {"held": "held.", "failed": "failed.", "undecided": "is undecided by this experiment."}[outcome])
    lines.append("Scope: this measures the uploaded code (or the stated re-implementation) under this harness, "
                 "these settings and these seeds. It does not prove a general theorem.")
    return lines


def summarise_for_model(plan, record):
    """The measured result as Nemotron sees it before a follow-up: numbers from CounterLab only."""
    return {"complete": record["complete"], "reproduced": record["reproduced"],
            "measurements": {metric: {c: {k: v[k] for k in ("mean", "std", "min", "max")} for c, v in rows.items()}
                             for metric, rows in record["measurements"].items()},
            "verdicts": [{k: v.get(k) for k in ("explanation", "metric", "left", "relation", "right", "status",
                                                 "left_mean", "right_mean", "seeds_agreeing", "seeds_compared")}
                         for v in record["verdicts"]],
            "explanations": [{k: e[k] for k in ("id", "status")} for e in record["explanations"]],
            "errors": [e["error"][-600:] for e in record["errors"][:3]]}
