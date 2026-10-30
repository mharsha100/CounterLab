import counterlab_sandbox as sb

PAGES, LENGTH, CAPACITY = 60, 3000, 10
NOISE = {"noise_5": 5.0, "noise_100": 100.0}
IMPLEMENTATIONS = {"authors": "cache_refresh/authors/pge.py", "reproduction": "cache_refresh/reproduction/pge.py"}


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
    noise = [rng.gauss(0.0, NOISE[condition]) for _ in requests]
    predict = lambda t, page: truth[t] + noise[t]
    authors = sb.load(IMPLEMENTATIONS["authors"]).simulate(requests, CAPACITY, predict)
    reproduction = sb.load(IMPLEMENTATIONS["reproduction"]).simulate(requests, CAPACITY, predict)
    return {"refresh_gain": authors - reproduction}
