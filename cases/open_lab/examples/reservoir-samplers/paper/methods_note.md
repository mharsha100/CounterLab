# Methods note: uniform sampling from a stream (Algorithm R)

We need a uniform random sample of k items from a stream of unknown length n,
using O(k) memory. We use Algorithm R (Vitter, 1985):

1. Put the first k items into the reservoir.
2. For the item at zero-based position i (i >= k), draw j uniformly from
   {0, 1, ..., i}. If j < k, replace reservoir[j] with the new item.

**Claim.** After the stream ends, every item has probability exactly k/n of
being in the reservoir, independent of its position.

Two groups implemented the method for our data pipeline (`impl_a/reservoir.py`
and `impl_b/reservoir.py`). Group B reports that its downstream estimates of
the stream's early segment are consistently lower than group A's, and both
groups state that their implementation follows the steps above.
