"""Open investigations: bring a paper and/or code, and Nemotron designs a checked experiment.

The pipeline keeps CounterLab's evidence rules for arbitrary uploads:
predictions are committed before execution, a deterministic guard checks the
plan, uploaded code runs only in an isolated sandbox, every measurement is
repeated, and the report is written by code from the measurements.
"""

VERSION = "open_investigation_v1"
