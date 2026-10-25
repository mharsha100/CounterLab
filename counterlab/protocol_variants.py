"""Controlled timing intervention on our own reference; no external source code."""

from counterlab.learning_paging import ReferencePager


class HistoryTimingPager(ReferencePager):
    """Change only when the gate's history value is refreshed.

    All cache, prediction, and random-priority behavior stays in the same
    independently written base implementation. These are diagnostic variants,
    not full reproductions of either external report.
    """

    def __init__(self, capacity, *, history_refresh="after_miss", seed=0, tau=1):
        if history_refresh not in ("after_miss", "after_request"):
            raise ValueError("History refresh must be after_miss or after_request.")
        super().__init__(capacity, seed=seed, tau=tau)
        self.history_refresh = history_refresh

    def step(self, page, predicted_next):
        history_before = self.last_miss_unrevealed
        event = super().step(page, predicted_next)
        if self.history_refresh == "after_request":
            self.last_miss_unrevealed = self.layers.unrevealed
        return {**event, "history_before": history_before,
                "history_after": self.last_miss_unrevealed,
                "supplied_prediction": predicted_next}


def run_history_variant(requests, capacity, predictions, *, history_refresh, seed=0, tau=1):
    if len(predictions) != len(requests):
        raise ValueError("Supply one prediction for each request.")
    pager = HistoryTimingPager(capacity, history_refresh=history_refresh, seed=seed, tau=tau)
    events = [pager.step(page, score) for page, score in zip(requests, predictions)]
    return {"history_refresh": history_refresh, "result": pager.result().to_dict(),
            "gate_credits": pager.gate_credits, "events": events}
