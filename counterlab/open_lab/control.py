"""Shared control signals for a running open investigation."""


class InvestigationCancelled(Exception):
    """The person stopped the investigation. Saved steps stay in the record."""
