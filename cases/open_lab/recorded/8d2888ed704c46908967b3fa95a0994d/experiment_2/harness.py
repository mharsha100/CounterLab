import math
import statistics
import counterlab_sandbox as sb

N = 1000
OFFSETS = {"offset_1e4": 1e4, "offset_1e8": 1e8}


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
    xs = [rng.gauss(OFFSETS[condition], 1.0) for _ in range(N)]
    exact = statistics.pvariance(xs)  # exact rational arithmetic on the same floats
    estimate = naive(xs)
    error = abs(estimate - exact) / exact
    return {"log10_rel_error": math.log10(max(error, 1e-18))}
