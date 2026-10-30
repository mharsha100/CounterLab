"""Simulated planning for offline tests and the labelled preview. Never a model result.

Plans are written by the developers for the bundled examples. They exercise the
real guard, repair loop, sandbox, repeat check and report. Every record made
with them says ``simulated_provider``.
"""

import json

from counterlab.investigator import MODELS

RESERVOIR_HARNESS = '''import counterlab_sandbox as sb

IMPLEMENTATIONS = {"impl_a": "{prefix}impl_a/reservoir.py", "impl_b": "{prefix}impl_b/reservoir.py"}
N, K, TRIALS = 100, 5, 2000


def measure(condition, seed):
    module = sb.load(IMPLEMENTATIONS[condition])
    rng = sb.rng(seed)
    counts = [0] * N
    for _ in range(TRIALS):
        for item in module.reservoir_sample(range(N), K, rng=rng):
            counts[item] += 1
    expected = TRIALS * K / N
    return {"first_k_ratio": sum(counts[:K]) / (K * expected),
            "rest_ratio": sum(counts[K:]) / ((N - K) * expected)}
'''

RESERVOIR_FOLLOWUP = '''import counterlab_sandbox as sb

SIZES = {"k2": 2, "k10": 10}
N, TRIALS = 100, 2000


def measure(condition, seed):
    module = sb.load("reservoir_samplers/impl_b/reservoir.py")
    k = SIZES[condition]
    rng = sb.rng(seed)
    counts = [0] * N
    for _ in range(TRIALS):
        for item in module.reservoir_sample(range(N), k, rng=rng):
            counts[item] += 1
    expected = TRIALS * k / N
    return {"first_k_ratio": sum(counts[:k]) / (k * expected)}
'''

WELFORD_HARNESS = '''import math
import statistics
import counterlab_sandbox as sb

N, OFFSET = 1000, 1e8


def naive(xs):
    s1 = s2 = 0.0
    for x in xs:
        s1 += x
        s2 += x * x
    n = len(xs)
    return s2 / n - (s1 / n) ** 2


def welford(xs):
    n, mean, m2 = 0, 0.0, 0.0
    for x in xs:
        n += 1
        d = x - mean
        mean += d / n
        m2 += d * (x - mean)
    return m2 / n


def measure(condition, seed):
    rng = sb.rng(seed)
    xs = [rng.gauss(OFFSET, 1.0) for _ in range(N)]
    exact = statistics.pvariance(xs)  # exact rational arithmetic on the same floats
    estimate = {"naive": naive, "welford": welford}[condition](xs)
    error = abs(estimate - exact) / exact
    return {"log10_rel_error": math.log10(max(error, 1e-18))}
'''

WELFORD_FOLLOWUP = WELFORD_HARNESS.replace("N, OFFSET = 1000, 1e8", "N = 1000\nOFFSETS = {\"offset_1e4\": 1e4, \"offset_1e8\": 1e8}") \
    .replace("xs = [rng.gauss(OFFSET, 1.0) for _ in range(N)]", "xs = [rng.gauss(OFFSETS[condition], 1.0) for _ in range(N)]") \
    .replace('estimate = {"naive": naive, "welford": welford}[condition](xs)', "estimate = naive(xs)")

CACHE_HARNESS = '''import counterlab_sandbox as sb

PAGES, LENGTH, CAPACITY, NOISE = 60, 3000, 10, 40.0
IMPLEMENTATIONS = {"authors": "{prefix}authors/pge.py", "reproduction": "{prefix}reproduction/pge.py"}


def trace(rng):
    loop = list(range(0, 24))
    requests = []
    while len(requests) < LENGTH:
        if rng.random() < 0.7:
            requests.extend(loop[:rng.randint(8, 24)])
        else:
            requests.extend(rng.randrange(PAGES) for _ in range(rng.randint(1, 6)))
    return requests[:LENGTH]


def next_use(requests):
    upcoming, last = [0] * len(requests), {}
    for t in range(len(requests) - 1, -1, -1):
        upcoming[t] = last.get(requests[t], len(requests) + 1000)
        last[requests[t]] = t
    return upcoming


def measure(condition, seed):
    rng = sb.rng(seed)
    requests = trace(rng)
    truth = next_use(requests)
    noise = [rng.gauss(0.0, NOISE) for _ in requests]
    predict = lambda t, page: truth[t] + noise[t]
    module = sb.load(IMPLEMENTATIONS[condition])
    return {"misses": module.simulate(requests, CAPACITY, predict)}
'''

CACHE_FOLLOWUP = CACHE_HARNESS.replace("PAGES, LENGTH, CAPACITY, NOISE = 60, 3000, 10, 40.0",
                                       "PAGES, LENGTH, CAPACITY = 60, 3000, 10\nNOISE = {\"noise_5\": 5.0, \"noise_100\": 100.0}") \
    .replace("noise = [rng.gauss(0.0, NOISE) for _ in requests]", "noise = [rng.gauss(0.0, NOISE[condition]) for _ in requests]") \
    .replace("""    module = sb.load(IMPLEMENTATIONS[condition])
    return {"misses": module.simulate(requests, CAPACITY, predict)}""",
             """    authors = sb.load(IMPLEMENTATIONS["authors"]).simulate(requests, CAPACITY, predict)
    reproduction = sb.load(IMPLEMENTATIONS["reproduction"]).simulate(requests, CAPACITY, predict)
    return {"refresh_gain": authors - reproduction}""")


def _expected(metric, left, relation, right, tolerance):
    return {"metric": metric, "left": left, "relation": relation, "right": right, "tolerance": tolerance}


def plans():
    return {
        "reservoir": {
            "title": "Do both reservoir samplers give every item the same chance?",
            "question": "Does each implementation include every stream position with probability k/n?",
            "claim": {"statement": "Algorithm R includes every item with probability exactly k/n.", "source": "paper",
                      "evidence_quote": "every item has probability exactly k/n of being in the reservoir"},
            "factor": "Which implementation draws the replacement index",
            "explanations": [
                {"id": "E1", "statement": "Both implementations are uniform; group B's lower early estimates are noise.",
                 "expected": [_expected("first_k_ratio", "impl_b", "equal", "impl_a", 0.05)]},
                {"id": "E2", "statement": "impl_b draws j from {0..i-1}, so the first k items are evicted too often and under-represented.",
                 "expected": [_expected("first_k_ratio", "impl_b", "less", "impl_a", 0.05)]}],
            "bet": "E2",
            "conditions": [{"id": "impl_a", "label": "Group A", "description": "impl_a/reservoir.py, j uniform over {0..i}"},
                           {"id": "impl_b", "label": "Group B", "description": "impl_b/reservoir.py, j uniform over {0..i-1}"}],
            "metrics": [{"id": "first_k_ratio", "label": "First-k inclusion ratio", "unit": "x expected",
                         "description": "Inclusion frequency of the first k stream items divided by k/n (1.0 = uniform)."},
                        {"id": "rest_ratio", "label": "Remaining-items inclusion ratio", "unit": "x expected",
                         "description": "Same ratio for items k..n-1."}],
            "seeds": [1, 2, 3, 4, 5],
            "implementation_note": "Calls each uploaded reservoir_sample on range(100) with k=5, 2,000 times per seed, using the same random stream for both.",
            # First draft forgets the archive folder, so the repair loop is exercised.
            "harness_code": RESERVOIR_HARNESS.replace("{prefix}", "")},
        "reservoir_fix": RESERVOIR_HARNESS.replace("{prefix}", "reservoir_samplers/"),
        "reservoir_followup": {
            "title": "Does group B's bias depend on the reservoir size?",
            "question": "Does the under-sampling of the first k items shrink as k grows?",
            "claim": {"statement": "impl_b under-samples the first k items.", "source": "code", "evidence_quote": "rng.randint(0, i - 1)"},
            "factor": "Reservoir size k in impl_b",
            "explanations": [
                {"id": "E3", "statement": "The bias is about 1/k: the first-k ratio is near (k-1)/k, so larger reservoirs hide it.",
                 "expected": [_expected("first_k_ratio", "k10", "greater", "k2", 0.2)]},
                {"id": "E4", "statement": "The bias depends on stream length, not on k.",
                 "expected": [_expected("first_k_ratio", "k10", "equal", "k2", 0.05)]}],
            "bet": "E3",
            "conditions": [{"id": "k2", "label": "k = 2", "description": "impl_b with a 2-item reservoir"},
                           {"id": "k10", "label": "k = 10", "description": "impl_b with a 10-item reservoir"}],
            "metrics": [{"id": "first_k_ratio", "label": "First-k inclusion ratio", "unit": "x expected",
                         "description": "Inclusion frequency of the first k items divided by k/n."}],
            "seeds": [1, 2, 3, 4, 5],
            "implementation_note": "Only impl_b, n=100, 2,000 trials per seed.",
            "harness_code": RESERVOIR_FOLLOWUP},
        "welford": {
            "title": "Welford versus the one-pass formula at a large offset",
            "question": "Is Welford's algorithm more accurate when the mean is large relative to the spread?",
            "claim": {"statement": "The one-pass formula loses accuracy roughly with (mean/sd)^2; Welford stays accurate.",
                      "source": "paper", "evidence_quote": "its relative error grows roughly with (mean / standard deviation)^2"},
            "factor": "Variance algorithm",
            "explanations": [
                {"id": "E1", "statement": "Catastrophic cancellation ruins the one-pass formula; Welford avoids it.",
                 "expected": [_expected("log10_rel_error", "welford", "less", "naive", 3.0)]},
                {"id": "E2", "statement": "In double precision both are about equally accurate at this scale.",
                 "expected": [_expected("log10_rel_error", "welford", "equal", "naive", 1.0)]}],
            "bet": "E1",
            "conditions": [{"id": "naive", "label": "One-pass formula", "description": "S2/n - (S1/n)^2"},
                           {"id": "welford", "label": "Welford", "description": "Online mean and M2 update"}],
            "metrics": [{"id": "log10_rel_error", "label": "log10 relative error", "unit": "log10",
                         "description": "log10 of |estimate - exact| / exact, exact from rational arithmetic on the same data."}],
            "seeds": [1, 2, 3, 4, 5],
            "implementation_note": "No code was uploaded; both algorithms are implemented from the paper's description.",
            "harness_code": WELFORD_HARNESS},
        "welford_followup": {
            "title": "Does the one-pass error grow with the offset?",
            "question": "Does the one-pass formula's error grow as the mean moves away from zero?",
            "claim": {"statement": "Relative error grows roughly with (mean/sd)^2.", "source": "paper",
                      "evidence_quote": "grows roughly with (mean / standard deviation)^2"},
            "factor": "Mean offset of the data (one-pass formula only)",
            "explanations": [
                {"id": "E3", "statement": "Error grows with the offset: about 8 orders of magnitude from 1e4 to 1e8.",
                 "expected": [_expected("log10_rel_error", "offset_1e8", "greater", "offset_1e4", 4.0)]},
                {"id": "E4", "statement": "Error does not depend on the offset.",
                 "expected": [_expected("log10_rel_error", "offset_1e8", "equal", "offset_1e4", 1.0)]}],
            "bet": "E3",
            "conditions": [{"id": "offset_1e4", "label": "Mean 1e4", "description": "Data ~ N(1e4, 1)"},
                           {"id": "offset_1e8", "label": "Mean 1e8", "description": "Data ~ N(1e8, 1)"}],
            "metrics": [{"id": "log10_rel_error", "label": "log10 relative error", "unit": "log10",
                         "description": "One-pass formula error against exact rational variance."}],
            "seeds": [1, 2, 3, 4, 5],
            "implementation_note": "Implemented from the paper's description.",
            "harness_code": WELFORD_FOLLOWUP},
        "cache": {
            "title": "Does refresh timing explain the two miss counts?",
            "question": "Is refreshing predictions only on misses what separates the authors' and the reproduction's miss counts?",
            "claim": {"statement": "Whenever a page is requested, its stored prediction is updated.", "source": "paper_and_code",
                      "evidence_quote": "Whenever a page is requested, its stored prediction is updated"},
            "factor": "When a cached page's prediction is refreshed",
            "explanations": [
                {"id": "E1", "statement": "Stale predictions on hits make the authors' code evict pages that are about to be used, so it misses more.",
                 "expected": [_expected("misses", "authors", "greater", "reproduction", 0)]},
                {"id": "E2", "statement": "Refresh timing does not matter; the reported difference comes from something else.",
                 "expected": [_expected("misses", "authors", "equal", "reproduction", 15)]}],
            "bet": "E1",
            "conditions": [{"id": "authors", "label": "Authors (refresh on miss)", "description": "authors/pge.py"},
                           {"id": "reproduction", "label": "Reproduction (refresh every request)", "description": "reproduction/pge.py"}],
            "metrics": [{"id": "misses", "label": "Cache misses", "unit": "misses",
                         "description": "Misses over a 3,000-request looping trace, 10-page cache, prediction noise sd 40."}],
            "seeds": [11, 12, 13, 14, 15, 16],
            "implementation_note": "Both uploaded simulate() functions get the identical trace and identical noisy predictions per seed.",
            "harness_code": CACHE_HARNESS.replace("{prefix}", "cache_refresh/")},
        "cache_followup": {
            "title": "Does the refresh effect depend on prediction quality?",
            "question": "Does refreshing on every request help with accurate predictions and hurt with noisy ones?",
            "claim": {"statement": "Refresh timing changes miss counts.", "source": "code",
                      "evidence_quote": "cache[page] = predict(t, page)  # refresh on every request"},
            "factor": "Prediction noise (both implementations measured on each trace)",
            "explanations": [
                {"id": "E3", "statement": "Fresh predictions help only when they are accurate; with noisy predictions, refreshing on every request adds noise to every hit and hurts.",
                 "expected": [_expected("refresh_gain", "noise_5", "greater", "noise_100", 50)]},
                {"id": "E4", "statement": "Prediction noise does not change the effect of refresh timing.",
                 "expected": [_expected("refresh_gain", "noise_5", "equal", "noise_100", 30)]}],
            "bet": "E3",
            "conditions": [{"id": "noise_5", "label": "Accurate predictions (sd 5)", "description": "Gaussian noise sd 5 on the true next-request time"},
                           {"id": "noise_100", "label": "Noisy predictions (sd 100)", "description": "Gaussian noise sd 100"}],
            "metrics": [{"id": "refresh_gain", "label": "Misses saved by refreshing", "unit": "misses",
                         "description": "Authors' misses minus the reproduction's misses on the same trace (positive: refreshing helps)."}],
            "seeds": [11, 12, 13, 14, 15, 16],
            "implementation_note": "Each call runs both uploaded simulate() functions on the same trace and predictions.",
            "harness_code": CACHE_FOLLOWUP.replace("{prefix}", "cache_refresh/")},
    }


def which(body):
    text = json.dumps(body["messages"])
    if "reservoir" in text:
        return "reservoir"
    if "pge.py" in text:
        return "cache"
    return "welford"


def simulated_transport(key, route, body=None):
    """Drop-in replacement for the Token Factory transport. Never contacts a network."""
    if route == "models":
        return {"data": [{"id": MODELS[0]}]}
    if body["response_format"]["json_schema"]["name"] == "counterlab_probe":
        return {"model": MODELS[0], "usage": {"prompt_tokens": 60, "completion_tokens": 12, "total_tokens": 72},
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(
                    {"status": "ready", "model_family": "Nemotron (simulated)"})}}]}
    case, table = which(body), plans()
    name = body["response_format"]["json_schema"]["name"]
    followup = "first_experiment_measurements" in body["messages"][-1]["content"]
    if name == "counterlab_harness_repair":
        content = {"change_summary": "Load the uploaded files through the archive folder they were unpacked into.",
                   "harness_code": table.get(f"{case}_fix", table[case]["harness_code"])}
    elif followup:
        content = table.get(f"{case}_followup")
        if content is None:
            return {"model": MODELS[0], "usage": {}, "choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]}
    else:
        content = table[case]
    tokens = len(json.dumps(body)) // 4
    return {"model": MODELS[0], "usage": {"prompt_tokens": tokens, "completion_tokens": 900, "total_tokens": tokens + 900},
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(content)}}]}
