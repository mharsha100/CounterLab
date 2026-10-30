import counterlab_sandbox as sb

IMPLEMENTATIONS = {"impl_a": "reservoir_samplers/impl_a/reservoir.py", "impl_b": "reservoir_samplers/impl_b/reservoir.py"}
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
