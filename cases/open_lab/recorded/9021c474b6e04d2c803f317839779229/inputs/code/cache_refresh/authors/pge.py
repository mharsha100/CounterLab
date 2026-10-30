"""Prediction-guided eviction, authors' implementation."""


def simulate(requests, capacity, predict):
    """Run PGE over a request list.

    predict(t, page) returns the predicted time of the page's next request,
    given the request at time t. Returns the number of misses.
    """
    cache = {}  # page -> stored predicted next-request time
    misses = 0
    for t, page in enumerate(requests):
        if page in cache:
            continue  # hit: keep the stored prediction (refreshed when the page was loaded)
        misses += 1
        if len(cache) >= capacity:
            victim = max(cache, key=lambda p: (cache[p], -p))
            del cache[victim]
        cache[page] = predict(t, page)
    return misses
