"""Full finite cache-cost oracle, independent of the layer implementation.

Enumerates reachable cache states and prefix costs. Source forecasts and initial
state are explicit inputs. No production pager, layers or external code import.
"""
import hashlib
import json
import math
import random
import struct


def digest(value):
    return hashlib.sha256((json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()).hexdigest()


def optimal(states):
    best = min(states.values())
    return {cache for cache, cost in states.items() if cost == best}


def uncertainty(configurations, capacity):
    forced = set.intersection(*(set(cache) for cache in configurations))
    return capacity - len(forced)


def advance(states, page, capacity):
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
    if len(following) > 64:
        raise ValueError("Independent reachable-state budget exceeded.")
    return following


def replay_batch(data, seed):
    requests, forecasts, capacity = data["requests"], data["predictions"], data["capacity"]
    start, initial = data["start"], data["initial"]
    if (type(capacity) is not int or not 2 <= capacity <= 32 or not capacity <= len(requests) <= 8192
            or len(forecasts) != len(requests) or len(set(initial)) != capacity
            or not capacity <= start <= len(requests)
            or any(type(page) is not int or not 0 <= page <= capacity for page in requests)):
        raise ValueError("Independent source oracle inputs exceed the reviewed bounds.")
    rng = random.Random(seed)
    tape = [rng.random() for _ in range(capacity + len(requests) - start)]
    last_forecasts = {page: forecasts[index] for index, page in enumerate(requests[:start])}
    arms = [{"tau": tau, "history": history, "seed": seed, "misses_after_warmup": 0,
             "gate_credits": 0, "tie_count": 0, "cache": set(initial),
             "ranks": dict(zip(initial, tape[:capacity])), "scores": dict(last_forecasts),
             "budget": 0, "saved": 0, "trace": hashlib.sha256()}
            for tau, history in ((0, "after_request"), (1, "after_request"), (1, "after_miss"))]
    states = {frozenset(initial): capacity}
    before = optimal(states)
    for index in range(start, len(requests)):
        page = requests[index]
        entering = all(page not in cache for cache in before)
        u_before = uncertainty(before, capacity)
        states = advance(states, page, capacity)
        after = optimal(states)
        u_after = uncertainty(after, capacity)
        for arm in arms:
            cache, ranks, scores = arm["cache"], arm["ranks"], arm["scores"]
            hit, previous_budget, previous_y = page in cache, arm["budget"], arm["saved"]
            victim, earned, decision, candidates = -1, False, 0, set()
            if not hit:
                arm["misses_after_warmup"] += 1
                candidates = {resident for resident in cache if frozenset((cache - {resident}) | {page}) in after}
                if not candidates:
                    raise ValueError("No legal eviction in the independent optimal-state family.")
                if entering:
                    arm["budget"], prediction_branch, decision = arm["tau"], True, 1
                else:
                    earned = u_before <= (previous_y + 2) / math.e - 2
                    if earned:
                        arm["gate_credits"] += 1
                        arm["budget"] += 1
                    prediction_branch = arm["budget"] > 0
                    if prediction_branch:
                        arm["budget"] -= 1
                    decision = 2 if prediction_branch else 3
                key = (lambda resident: (scores[resident], ranks[resident])) if prediction_branch else (lambda resident: ranks[resident])
                victim = (max if prediction_branch else min)(candidates, key=key)
                arm["tie_count"] += sum(key(resident) == key(victim) for resident in candidates) - 1
                cache.remove(victim)
                cache.add(page)
            if frozenset(cache) not in after:
                raise ValueError("Independent cache is outside the prefix-optimal family.")
            ranks[page], scores[page] = tape[capacity + index - start], forecasts[index]
            if not hit or arm["history"] == "after_request":
                arm["saved"] = u_after
            arm["trace"].update(struct.pack("<12q", index, page, int(hit), u_before, previous_y,
                previous_budget, arm["budget"], int(earned), victim,
                sum(1 << resident for resident in cache), sum(1 << resident for resident in candidates), decision))
        before = after
    return [{**{name: arm[name] for name in ("tau", "history", "seed", "misses_after_warmup", "gate_credits", "tie_count")},
             "trace_sha256": arm["trace"].hexdigest(), "priority_tape_sha256": digest(tape), "priority_draws": len(tape)} for arm in arms]
