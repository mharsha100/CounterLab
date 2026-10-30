import counterlab_sandbox as sb

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
