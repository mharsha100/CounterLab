import counterlab_sandbox as sb
import numpy as np

def measure(condition: str, seed: int) -> dict[str, float]:
    # Load the two implementations
    mod_authors = sb.load("cache_refresh/authors/pge.py")
    mod_repro = sb.load("cache_refresh/reproduction/pge.py")
    
    # Deterministic RNG for this seed
    rng = sb.rng(seed)
    
    # Generate a fixed trace: 5 pages cycling, 200 cycles = 1000 requests
    n_pages = 5
    n_cycles = 200
    trace = [i % n_pages for i in range(n_cycles * n_pages)]  # [0,1,2,3,4, 0,1,2,3,4, ...]
    n = len(trace)
    
    # Pre-compute true next-request time for each (t, page)
    # large number if no future request
    INF = 10_000
    true_next = [[INF] * n_pages for _ in range(n)]
    # For each page, scan backwards to fill next occurrence
    for p in range(n_pages):
        next_seen = INF
        for t in range(n - 1, -1, -1):
            true_next[t][p] = next_seen
            if trace[t] == p:
                next_seen = t
    
    # Pre-compute noise for each (t, page)
    noise_std = 2.0
    noise = [[rng.gauss(0.0, noise_std) for _ in range(n_pages)] for _ in range(n)]
    
    def predict(t: int, page: int) -> float:
        return true_next[t][page] + noise[t][page]
    
    capacity = 3
    
    if condition == "authors":
        misses = mod_authors.simulate(trace, capacity, predict)
    elif condition == "reproduction":
        misses = mod_repro.simulate(trace, capacity, predict)
    else:
        raise ValueError(f"Unknown condition: {condition}")
    
    return {"misses": float(misses)}