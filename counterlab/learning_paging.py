"""Independent finite reference for the paper's exact-layer RPB-OM rules.

Specification: https://arxiv.org/html/2606.01342v3 (Eq. 3, Algorithm 3).
Priority ordering: https://cs.au.dk/~gerth/papers/tocs15.pdf (Section 3.1).
This deliberately uses exact layers without forgiveness or optimized data
structures. It is not a reproduction of the paper's benchmark implementation.
"""

import math
import random

from counterlab.paging import PagingResult, validate


class ExactLayers:
    """Track prefix-optimal configurations without seeing future requests."""

    def __init__(self, capacity):
        validate([], capacity)
        self.capacity = capacity
        self.layers = [set() for _ in range(capacity)]

    @property
    def support(self):
        return set().union(*self.layers)

    @property
    def full(self):
        return bool(self.layers[0])

    def locate(self, page):
        return next((index for index, layer in enumerate(self.layers, 1) if page in layer), 0)

    @property
    def unrevealed(self):
        if not self.full:
            return 0
        for index in range(self.capacity - 1, -1, -1):
            if len(self.layers[index]) != 1:
                return index + 1
        return 0

    def advance(self, page):
        validate([page], self.capacity)
        location = self.locate(page)
        if not self.full and not location:
            # Cold start: fill one empty leading slot with the new page.
            self.layers = self.layers[1:] + [{page}]
        elif location == 0:
            if self.capacity == 1:
                self.layers = [{page}]
            else:
                self.layers = (self.layers[:-2]
                               + [self.layers[-2] | self.layers[-1], {page}])
        elif location == 1:
            self.layers = self.layers[1:] + [{page}]
        else:
            index = location - 1
            self.layers = (self.layers[:index - 1]
                           + [(self.layers[index - 1] | self.layers[index]) - {page}]
                           + self.layers[index + 1:] + [{page}])

    def valid_cache(self, cache):
        cache = set(cache)
        if not self.full:
            return cache == self.support
        if len(cache) != self.capacity or not cache <= self.support:
            return False
        prefix = set()
        for index, layer in enumerate(self.layers, 1):
            prefix |= layer
            if len(cache & prefix) > index:
                return False
        return True

    def eviction_candidates(self, cache, page):
        location = self.locate(page)
        if not location:
            return set(cache)
        prefix = set()
        for index, layer in enumerate(self.layers, 1):
            prefix |= layer
            if index >= location and len(cache & prefix) == index:
                return cache & prefix
        raise RuntimeError("No legal eviction candidate set found.")


class ReferencePager:
    """Online interface: one requested page and its supplied prediction per step.

    The cache does not receive a request trace or a future-reading callback.
    Random priority ranks are inserted uniformly when a page enters support;
    existing relative ranks persist until those pages leave support.
    """

    def __init__(self, capacity, *, policy="rpb_om", seed=0, tau=1):
        validate([], capacity)
        if policy not in ("online_min", "rpb_om"):
            raise ValueError("Reference policy must be online_min or rpb_om.")
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError("Seed must be an integer from 0 to 2**32 - 1.")
        if type(tau) is not int or not 0 <= tau <= 64:
            raise ValueError("Tau must be an integer from 0 to 64.")
        self.capacity, self.policy, self.tau = capacity, policy, tau
        self.layers = ExactLayers(capacity)
        self.cache = set()
        self.predictions = {}
        self.priority_order = []  # Low to high; integer ranks avoid float ties.
        self.rng = random.Random(seed)
        self.budget = 0
        self.last_miss_unrevealed = 0
        self.requests = self.misses = self.gate_credits = 0

    def step(self, page, predicted_next):
        validate([page], self.capacity)
        if (type(predicted_next) not in (int, float)
                or not math.isfinite(predicted_next)):
            raise ValueError("The supplied prediction must be a finite number.")
        if self.requests >= 10_000:
            raise ValueError("Reference runs are limited to 10,000 requests.")
        hit = page in self.cache
        location = self.layers.locate(page)
        before_budget = self.budget
        gate_earned = False
        victim = None
        decision = "hit"
        if not hit:
            self.misses += 1
            if len(self.cache) < self.capacity:
                decision = "warmup"
            else:
                candidates = self.layers.eviction_candidates(self.cache, page)
                use_prediction = False
                if self.policy == "rpb_om":
                    if location == 0:
                        self.budget = self.tau
                        use_prediction = True
                        decision = "l0_prediction"
                    else:
                        threshold = (self.last_miss_unrevealed + 2) / math.e - 2
                        if self.layers.unrevealed <= threshold:
                            self.budget += 1
                            self.gate_credits += 1
                            gate_earned = True
                        if self.budget > 0:
                            self.budget -= 1
                            use_prediction = True
                            decision = "support_prediction"
                        else:
                            decision = "support_priority"
                else:
                    decision = "online_min_priority"
                if use_prediction:
                    victim = max(candidates, key=lambda p: (self.predictions[p], p))
                else:
                    ranks = {p: rank for rank, p in enumerate(self.priority_order)}
                    victim = min(candidates, key=lambda p: ranks[p])
                self.cache.remove(victim)
                del self.predictions[victim]
            self.cache.add(page)
        self.predictions[page] = predicted_next
        self.layers.advance(page)
        support = self.layers.support
        self.priority_order = [p for p in self.priority_order if p in support]
        if page not in self.priority_order:
            self.priority_order.insert(self.rng.randrange(len(self.priority_order) + 1), page)
        if not hit:
            # Update after the miss has been served; hits must not reset Y.
            self.last_miss_unrevealed = self.layers.unrevealed
        self.requests += 1
        if (not self.layers.valid_cache(self.cache) or self.budget < 0
                or set(self.priority_order) != support):
            raise RuntimeError("Reference paging invariant failed.")
        return {"index": self.requests - 1, "page": page, "hit": hit,
                "layer_before": location, "evicted": victim, "decision": decision,
                "gate_earned": gate_earned, "budget_before": before_budget,
                "budget_after": self.budget, "unrevealed_after": self.layers.unrevealed}

    def result(self):
        return PagingResult(self.policy + "_exact_layers", self.capacity,
                            self.requests, self.requests - self.misses, self.misses)


def generated_advice(requests, mode):
    """Lab-only advice generator; future knowledge stays outside the pager.

    Perfect scores are next-request indices. Inverted scores reverse that
    ranking while remaining beyond the trace horizon. Both are synthetic
    diagnostics, not learned predictors or a claimed worst-case adversary.
    """
    sequence = validate(requests, 1)
    if mode not in ("perfect", "inverted"):
        raise ValueError("Advice mode must be perfect or inverted.")
    next_indices = [len(sequence)] * len(sequence)
    seen = {}
    for index in range(len(sequence) - 1, -1, -1):
        page = sequence[index]
        next_indices[index] = seen.get(page, len(sequence))
        seen[page] = index
    if mode == "inverted":
        return [2 * len(sequence) + 2 - value for value in next_indices]
    return next_indices


def run_reference(requests, capacity, *, advice_mode="perfect", policy="rpb_om", seed=0, tau=1):
    sequence = validate(requests, capacity)
    advice = generated_advice(sequence, advice_mode)
    pager = ReferencePager(capacity, policy=policy, seed=seed, tau=tau)
    events = [pager.step(page, prediction) for page, prediction in zip(sequence, advice)]
    return {"result": pager.result().to_dict(), "events": events,
            "gate_credits": pager.gate_credits}
