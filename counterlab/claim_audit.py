"""Developer-framed claims derived from existing verified records, never a model verdict.

The compact evidence basis preserves original JSON pointers. Its hash detects
changes; verification reloads the sealed records rather than trusting that hash.
No new experiment, provider call or external source retrieval occurs here.
"""
import hashlib
import json

from counterlab.records import RecordError
from counterlab.source_evaluation_records import project_source_evaluation
from counterlab.source_records import project_source_regime
from counterlab.study_records import project_study

VERSION = "claim_audit_v1"
# The numerical study replays its results, but its static source audit also
# needs an independent anchor: rehashing a local manifest must not rewrite it.
SOURCE_AUDIT_SHA256 = "577549e65af685e5540c8cf5c8e656dcacd48fb6945e6e41a2244b90ef568368"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def resolve(data, pointer):
    """Resolve an absolute JSON pointer; array indices are explicit and bounded."""
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("A citation needs an absolute JSON pointer.")
    for part in pointer[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(data, list):
            if not part.isascii() or not part.isdecimal() or str(int(part)) != part:
                raise ValueError("Invalid citation array index.")
            data = data[int(part)]
        elif isinstance(data, dict):
            data = data[part]
        else:
            raise ValueError("Citation continues beyond a value.")
    return data


def evidence_basis(study, source, evaluation):
    def record(title, route, view, data):
        return {"title": title, "route": route, "view": view,
                "data": data, "data_sha256": digest(data)}
    return {
        "contracts": record("Controlled contract study", "/api/research-study", "controlled-study", {
            "protocol_sha256": study["protocol_sha256"], "source_contracts": study["source_contracts"],
            "summary": {"controls": study["summary"]["controls"]}}),
        "source": record("Selected supporting source slice", "/api/source-reproduction", "source-reproduction", {
            "protocol_sha256": source["protocol_sha256"], "source_metadata": source["source_metadata"],
            "protocol": source["protocol"], "summary": source["summary"],
            "observations": [{key: row[key] for key in ("seed", "input_sha256", "prediction_sha256", "warmup_length")}
                             for row in source["observations"]]}),
        "evaluation": record("Frozen source planning evaluation", "/api/source-evaluation", "source-evaluation", {
            "task_protocol_sha256": evaluation["task_protocol_sha256"],
            "execution_protocol_sha256": evaluation["execution_protocol_sha256"],
            "policies": evaluation["policies"], "limitations": evaluation["limitations"],
            "tasks": [{"task_id": row["task_id"], "question_scope": row["question_scope"]} for row in evaluation["tasks"]],
            "model_batch_calls": evaluation["model_results"]["attempted_inference_requests"]}),
    }


def build_report(records):
    """Only call with evidence returned by the existing sealed-record verifiers."""
    source = records["source"]["data"]
    summary = source["summary"]
    policies = records["evaluation"]["data"]["policies"]
    adaptive = next(row for row in policies if row["policy"] == "adaptive_two_turn")
    heuristic = next(row for row in policies if row["policy"] == "contract_heuristic")
    pairs = summary["history_intervention"]
    deltas = [row["after_miss_misses"] - row["source_misses"] for row in pairs]
    changed = sum(delta != 0 for delta in deltas)
    matched = sum(row["matches"] for row in summary["rows"])
    if not pairs or not summary["rows"] or changed != summary["miss_difference_pairs"]:
        raise ValueError("Claim inputs disagree with the verified summary.")

    def cite(record, pointer, label):
        # Include the exact cited value for inspection, and require it to exist.
        return {"record": record, "pointer": pointer, "label": label,
                "value": resolve(records[record]["data"], pointer)}

    def check(label, state, detail):
        return {"label": label, "state": state, "detail": detail}

    claims = [
        {"id": "contracts", "title": "Do the reports compare the same contract?", "status": "documented",
         "label": "Documented differences", "view": "controlled-study",
         "answer": "The inspected implementations differ in history, priority, forecast delivery and miss-counting rules.",
         "scope": "A pinned static source audit. External implementations were inspected as text, not executed here.",
         "overstatement": "These differences explain the complete disagreement between the reports.",
         "checks": [check("Operational rules", "different", "Four differences are recorded in the pinned source audit."),
                    check("Reported plan versus driver", "different", "The prose and driver defaults differ; this does not identify every artifact's configuration."),
                    check("Full implementation parity", "unknown", "Static inspection cannot establish equivalent initialization, forgiveness or complete execution.")],
         "citations": [cite("contracts", "/source_contracts/differences", "Four operational differences"),
                       cite("contracts", "/source_contracts/static_checks", "Source-code line locators"),
                       cite("contracts", "/source_contracts/protocol_driver_mismatch", "Plan and driver comparison")],
         "missing": ["Reproduce both complete implementations under their own declared contracts before attributing the full disagreement."]},
        {"id": "reference", "title": "Did we match the selected reference numbers?", "status": "measured",
         "label": "Finite comparison", "view": "source-reproduction",
         "answer": f"{matched} of {len(summary['rows'])} selected supporting-report rows match our reconstruction.",
         "scope": f"One {summary['capacity']}-slot uniform trace with {summary['horizon']:,} requests. These are selected numerical rows, not the full paper or report.",
         "overstatement": "CounterLab reproduced the original paper and all published experiments.",
         "checks": [check("Metric and denominator", "matched", "Both sides use the same post-warmup offline-optimal denominator; exact OPT and mean/sample-standard-deviation tolerance 10^-12 are checked."),
                    check("Initialization and random schedule", "matched", "The source-specific first-distinct reset, stored forecasts and per-request draws are preserved."),
                    check("Full upstream file", "context", "Availability and hash verification in this environment are shown separately below. The three comparison rows remain pinned to the frozen record.")],
         "citations": [cite("source", "/summary/rows", "Every selected row, residual and denominator"),
                       cite("source", "/source_metadata", "Pinned numeric source and selection"),
                       cite("source", "/protocol/rules/metric", "Counting window")],
         "missing": ["Other source regimes, real traces, the official implementation and the full challenging report remain unreproduced."]},
        {"id": "timing", "title": "Can history timing change measured costs?", "status": "measured",
         "label": "Matched intervention", "view": "source-reproduction",
         "answer": f"Miss counts differ in {changed} of {len(pairs)} matched algorithm seeds in this source slice.",
         "scope": f"After-miss minus after-every-request ranges from {min(deltas):+d} to {max(deltas):+d} misses. The seeds share one request trace and are correlated.",
         "overstatement": "One history rule is always better, or this finite result refutes a theorem.",
         "checks": [check("One changed factor", "matched", "Only history refresh changes within each pair; budget reset, requests, forecasts, priority tape, initialization and counting window stay fixed."),
                    check("All paired seeds retained", "matched", f"All {len(pairs)} pairs are included, including any zero delta."),
                    check("Generalization", "unknown", "A finite synthetic slice does not establish a ranking across workloads or an asymptotic result.")],
         "citations": [cite("source", "/summary/history_intervention", "All paired costs and trace fingerprints"),
                       cite("source", "/protocol/rules/intervention", "Declared intervention"),
                       cite("source", "/protocol/rules/randomness", "Shared random schedule"),
                       cite("contracts", "/summary/controls", "Separate controlled-study null and optimum checks")],
         "missing": ["Independent workloads and complete implementation parity are needed for broader conclusions. The separate controls do not enlarge this source slice's denominator."]},
        {"id": "advantage", "title": "Has the model beaten the simple baseline?", "status": "open",
         "label": "Not established", "view": "source-evaluation",
         "answer": f"No selection advantage is established: adaptive Nemotron found {adaptive['differences_found']}/{adaptive['difference_tasks']} available differences; the contract heuristic found {heuristic['differences_found']}/{heuristic['difference_tasks']} with zero model calls.",
         "scope": "Eight frozen, correlated development tasks and one repeat. All four policies, rejected plans, prediction errors and truncated responses remain in the evaluation.",
         "overstatement": "The research agent outperforms a heuristic or is a generally reliable scientist.",
         "checks": [check("Shared tasks and scoring", "matched", "The policies use the same frozen choices, measurements and deterministic factual reporter."),
                    check("Prediction accuracy", "context", f"Both predictions matched on {adaptive['correct_predictions']}/{adaptive['predictions_checked']} checked adaptive tests versus {heuristic['correct_predictions']}/{heuristic['predictions_checked']} heuristic tests. Different choices mean these are descriptive counts, not matched independent trials."),
                    check("Guarded workflow v2 quality", "unknown", "Its saved integration uses simulated planning. The earlier real-model scores do not evaluate v2.")],
         "citations": [cite("evaluation", "/policies", "Complete four-policy score table"),
                       cite("evaluation", "/tasks", "Task IDs and scopes"),
                       cite("evaluation", "/limitations", "Frozen analysis limits")],
         "missing": ["A fresh preregistered, independently varied evaluation is required for a model-quality claim. No new batch is authorized by this audit."]},
        {"id": "verdict", "title": "Have we resolved the research disagreement?", "status": "open",
         "label": "Unresolved", "view": "controlled-study",
         "answer": "The full report disagreement and asymptotic claims remain unresolved.",
         "scope": "Static contract differences, selected source agreement and finite interventions support narrower claims. Unknown coverage is not evidence that two claims are incompatible.",
         "overstatement": "The paper is wrong, either report is disproved, or CounterLab proved an asymptotic bound.",
         "checks": [check("Finite source slice", "context", "A selected reconstruction and a controlled intervention are available."),
                    check("Both complete reports", "unknown", "The official implementation, forgiveness behavior, real traces and challenging lazy-adversary experiment are not reproduced."),
                    check("Asymptotic adjudication", "unknown", "These finite experiments do not prove or refute the theorem in its full stated setting.")],
         "citations": [cite("source", "/summary/full_reports_reproduced", "Full report coverage flag"),
                       cite("source", "/summary/official_implementation_parity_established", "Official parity flag"),
                       cite("source", "/summary/asymptotic_claim_adjudicated", "Theorem coverage flag"),
                       cite("contracts", "/source_contracts/conclusion_limit", "Source audit limit")],
         "missing": ["Close the missing contract and implementation coverage first. A theorem verdict additionally requires a valid mathematical argument under its stated assumptions."]},
    ]
    return {"version": VERSION, "framing": "Developer-framed questions; deterministic projection of verified records, not autonomous claim extraction or a model verdict.",
            "records": records, "claims": claims,
            "source_links": records["contracts"]["data"]["source_contracts"]["sources"],
            "limits": ["Record hashes detect byte changes; they are not signatures or trusted timestamps.",
                       "Citations address compact verified record fields. Original replay packages verify the underlying measurements.",
                       "No new experiment, model call or upstream retrieval is performed by this audit."]}


def project_claim_audit():
    try:
        study, source, evaluation = project_study(), project_source_regime(), project_source_evaluation()
        if digest(study["source_contracts"]) != SOURCE_AUDIT_SHA256:
            raise ValueError("The pinned static source audit changed.")
        if not evaluation["model_results"]:
            raise ValueError("The frozen evaluation is required.")
        report = build_report(evidence_basis(study, source, evaluation))
        return {"report": report, "report_sha256": digest(report), "inference_requests": 0, "worker_calls": 0,
                "verification": {"basis": "Existing sealed-record verifiers; selected comparison rows are bound to the frozen local record.",
                    "full_upstream_artifact_verified_here": source["verification"]["published_data_verified"],
                    "note": "The audit reloads verified records and derives its statements. It does not rerun the full long source experiment or independent full-trace oracle on page load."}}
    except (OSError, ValueError, KeyError, TypeError, StopIteration, IndexError):
        raise RecordError("Claim audit is unavailable or its source evidence failed verification.") from None


def verify_saved_audit(saved):
    """A matching self-hash alone is insufficient: derive the entire report again."""
    current = project_claim_audit()
    if (saved.get("report_sha256") != digest(saved.get("report"))
            or saved.get("report") != current["report"]):
        raise RecordError("Saved claim audit differs from the verified evidence and current derivation.")
    return {"status": "claim_audit_verified", "claims_checked": len(current["report"]["claims"]),
            "report_sha256": current["report_sha256"], "inference_requests": 0,
            "verification_context": current["verification"],
            "note": "Saved environment labels are not trusted; this context was checked locally. This does not reexecute every long experiment."}
