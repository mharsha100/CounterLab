import counterlab_sandbox as sb
import math

AUTHORS = sb.load("cache_refresh/authors/pge.py")
REPRODUCTION = sb.load("cache_refresh/reproduction/pge.py")

def parse_condition(cond):
    # Conditions are: authors_noise_0.0, reproduction_noise_0.0, etc.
    if cond.startswith("authors_"):
        policy = "authors"
        suffix = cond[8:]  # "noise_0.0"
    else:
        policy = "reproduction"
        suffix = cond[14:]  # "noise_0.0"
    # suffix is "noise_X.Y"
    noise_level = float(suffix[6:])  # skip "noise_"
    return policy, noise_level

def generate_trace(rng, n_pages=10, n_cycles=100):
    """Repeating pattern 0..n_pages-1."""
    base = list(range(n_pages))
    trace = []
    for _ in range(n_cycles):
        trace.extend(base)
    return trace

def precompute_true_next(trace):
    """For each t and page, true next access time after t."""
    n = len(trace)
    max_page = max(trace) + 1
    next_pos = [[float('inf')] * max_page for _ in range(n + 1)]
    last_seen = [float('inf')] * max_page
    for t in range(n - 1, -1, -1):
        page = trace[t]
        last_seen[page] = t
        for p in range(max_page):
            next_pos[t][p] = last_seen[p]
    return next_pos

def measure(condition: str, seed: int) -> dict[str, float]:
    policy, noise_level = parse_condition(condition)
    
    # Trace generation RNG
    rng_trace = sb.rng(seed)
    trace = generate_trace(rng_trace)
    n = len(trace)
    
    # Precompute true next access
    true_next = precompute_true_next(trace)
    
    # Noise RNG (separate stream, same for all conditions at this seed)
    rng_noise = sb.rng(seed + 10000)
    max_page = max(trace) + 1
    noise = [[0.0] * max_page for _ in range(n)]
    for t in range(n):
        for p in range(max_page):
            noise[t][p] = rng_noise.gauss(0.0, 1.0)
    
    # Predictor function
    def predict(t, page):
        tn = true_next[t][page]
        if tn == float('inf'):
            return float('inf')
        return tn + noise_level * noise[t][page]
    
    # Run simulation
    capacity = 3
    if policy == "authors":
        misses = AUTHORS.simulate(trace, capacity, predict)
    else:
        misses = REPRODUCTION.simulate(trace, capacity, predict)
    
    return {"misses": float(misses)}