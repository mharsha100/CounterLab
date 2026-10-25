"""Cold-start, mandatory-insertion paging baselines; no paper reproduction yet.

Each missing request costs one. On a miss, the requested page must enter the
cache, evicting a resident if full. Capacity and initialization are identical
for both policies. Offline MIN knows future requests and is an oracle baseline,
not an online algorithm available to a real cache.
"""

from collections import OrderedDict
from dataclasses import asdict, dataclass
from functools import lru_cache


MAX_REQUESTS = 10_000
MAX_CAPACITY = 64


@dataclass(frozen=True)
class PagingResult:
    policy: str
    capacity: int
    requests: int
    hits: int
    misses: int

    def to_dict(self):
        return asdict(self)


def validate(requests, capacity):
    if type(capacity) is not int or not 1 <= capacity <= MAX_CAPACITY:
        raise ValueError(f"Capacity must be an integer from 1 to {MAX_CAPACITY}.")
    if not isinstance(requests, (list, tuple)) or len(requests) > MAX_REQUESTS:
        raise ValueError(f"Requests must be a list/tuple of at most {MAX_REQUESTS} pages.")
    if any(type(page) is not int or page < 0 for page in requests):
        raise ValueError("Page IDs must be nonnegative integers, excluding booleans.")
    return tuple(requests)


def simulate(requests, capacity, policy):
    """Run a deterministic baseline with an initially empty cache."""
    sequence = validate(requests, capacity)
    if policy not in ("lru", "offline_min"):
        raise ValueError("Supported baseline policies are lru and offline_min.")
    misses = 0
    if policy == "lru":
        cache = OrderedDict()
        for page in sequence:
            if page in cache:
                cache.move_to_end(page)
            else:
                misses += 1
                if len(cache) == capacity:
                    cache.popitem(last=False)
                cache[page] = None
            if len(cache) > capacity or page not in cache:
                raise RuntimeError("Paging cache invariant failed.")
    else:
        # Precompute each request's next occurrence in a backward pass.
        next_use = [len(sequence)] * len(sequence)
        upcoming = {}
        for index in range(len(sequence) - 1, -1, -1):
            page = sequence[index]
            next_use[index] = upcoming.get(page, len(sequence))
            upcoming[page] = index
        cache = {}
        for index, page in enumerate(sequence):
            if page not in cache:
                misses += 1
                if len(cache) == capacity:
                    victim = max(cache, key=lambda resident: (cache[resident], resident))
                    del cache[victim]
            cache[page] = next_use[index]
            if len(cache) > capacity or page not in cache:
                raise RuntimeError("Paging cache invariant failed.")
    return PagingResult(policy, capacity, len(sequence), len(sequence) - misses, misses)


def exhaustive_minimum_misses(requests, capacity):
    """Independent tiny-case oracle: search all legal eviction choices.

    This oracle deliberately shares no future-use/eviction logic with MIN.
    Bounds keep its exponential state space out of normal experiments.
    """
    sequence = validate(requests, capacity)
    if len(sequence) > 12 or capacity > 4:
        raise ValueError("Exhaustive verification is restricted to length <= 12 and capacity <= 4.")

    @lru_cache(maxsize=None)
    def search(index, residents):
        if index == len(sequence):
            return 0
        page = sequence[index]
        if page in residents:
            return search(index + 1, residents)
        if len(residents) < capacity:
            updated = tuple(sorted((*residents, page)))
            return 1 + search(index + 1, updated)
        return 1 + min(
            search(index + 1, tuple(sorted((*[p for p in residents if p != victim], page))))
            for victim in residents
        )

    return search(0, ())
