"""Independent finite work-function oracle; no layers or production pager import.

Enumerates reachable cache configurations and their minimum prefix costs.
Forecasts and random draws are inputs, not generated or inferred here.
This checks finite mathematical semantics, not external implementation parity.
"""

import math
from functools import lru_cache

MAX_STATES = 256
MAX_REQUESTS = 1000


@lru_cache(maxsize=256)
def prefix_states(requests, capacity):
    if (type(capacity) is not int or not 1 <= capacity <= 64
            or not 1 <= len(requests) <= MAX_REQUESTS
            or any(type(page) is not int or page < 0 for page in requests)):
        raise ValueError("Oracle input is outside its finite limits.")
    states = {frozenset(): 0}
    schedule = [frozenset(states)]
    optimum = [0]
    for page in requests:
        following = {}
        for cache, cost in states.items():
            if page in cache:
                choices = [(cache, cost)]
            elif len(cache) < capacity:
                choices = [(cache | {page}, cost + 1)]
            else:
                choices = [((cache - {victim}) | {page}, cost + 1) for victim in cache]
            for new_cache, new_cost in choices:
                following[new_cache] = min(following.get(new_cache, math.inf), new_cost)
        if len(following) > MAX_STATES:
            raise ValueError("Oracle state budget exceeded.")
        states = following
        best = min(states.values())
        schedule.append(frozenset(cache for cache, cost in states.items() if cost == best))
        optimum.append(best)
    return tuple(schedule), tuple(optimum)


def support(configurations):
    return frozenset().union(*configurations)


def unrevealed(configurations, capacity):
    if not configurations or len(next(iter(configurations))) < capacity:
        return 0
    forced = set(next(iter(configurations)))
    for configuration in configurations:
        forced.intersection_update(configuration)
    return capacity - len(forced)


def run_oracle(requests, capacity, forecasts, priorities, profile, tau):
    """Legal victims lead to an independently computed prefix-optimal state."""
    requests = tuple(requests)
    schedule, optimum = prefix_states(requests, capacity)
    if (len(priorities) != len(requests) or len(forecasts) != len(requests)
            or type(tau) is not int or not 0 <= tau <= 64
            or set(profile) != {"history", "priority", "prediction"}
            or profile["history"] not in ("after_miss", "after_request")
            or profile["priority"] not in ("support_entry", "each_request")
            or profile["prediction"] not in ("stored_at_access", "fresh_at_decision")):
        raise ValueError("Invalid oracle contract.")
    cache, ranks, accessed = set(), {}, {}
    budget = history = misses = credits = 0
    events = []
    for index, page in enumerate(requests):
        before, after = schedule[index], schedule[index + 1]
        entering = page not in support(before)
        if entering:
            ranks[page] = priorities[index]
        hit = page in cache
        u = unrevealed(before, capacity)
        old_budget, old_history = budget, history
        decision, victim, earned, candidates = "hit", None, False, set()
        if not hit:
            misses += 1
            decision = "warmup"
            if len(cache) == capacity:
                candidates = {resident for resident in cache
                              if frozenset((cache - {resident}) | {page}) in after}
                if not candidates:
                    raise RuntimeError("No independently legal eviction from a valid cache.")
                if entering:
                    budget, predicted, decision = tau, True, "l0_prediction"
                else:
                    earned = u <= (history + 2) / math.e - 2
                    if earned:
                        budget += 1
                        credits += 1
                    predicted = budget > 0
                    if predicted:
                        budget -= 1
                    decision = "support_prediction" if predicted else "support_priority"
                if predicted:
                    scores = {resident: forecasts[index if profile["prediction"] == "fresh_at_decision"
                                                  else accessed[resident]][resident] for resident in candidates}
                    victim = sorted(candidates, key=lambda resident: (scores[resident], ranks[resident], resident))[-1]
                else:
                    victim = sorted(candidates, key=lambda resident: (ranks[resident], resident))[0]
                cache.remove(victim)
            cache.add(page)
        accessed[page] = index
        if profile["priority"] == "each_request":
            ranks[page] = priorities[index]
        ranks = {resident: rank for resident, rank in ranks.items() if resident in support(after)}
        if not hit or profile["history"] == "after_request":
            history = unrevealed(after, capacity)
        if frozenset(cache) not in after:
            raise RuntimeError("Oracle cache is not prefix-optimal.")
        events.append({"t": index, "page": page, "hit": hit, "U_before": u,
                       "Y_before": old_history, "B_before": old_budget, "B_after": budget,
                       "gate_earned": earned, "victim": victim, "candidates": sorted(candidates),
                       "decision": decision, "cache_after": sorted(cache)})
    return {"misses_cold": misses, "gate_credits": credits,
            "optimum_cold": optimum[-1], "events": events}
