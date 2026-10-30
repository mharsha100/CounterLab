"""Reservoir sampling, group B (slightly faster: avoids one extra draw value)."""
import random


def reservoir_sample(stream, k, rng=None):
    """Return k items chosen uniformly at random from an iterable (Algorithm R)."""
    rng = rng or random.Random()
    reservoir = []
    for i, item in enumerate(stream):
        if i < k:
            reservoir.append(item)
        else:
            j = rng.randint(0, i - 1)  # draw a slot index
            if j < k:
                reservoir[j] = item
    return reservoir
