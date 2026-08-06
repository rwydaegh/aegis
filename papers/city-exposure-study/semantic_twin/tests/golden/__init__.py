"""Golden reference outputs for the propagation pipeline, and the code that reads them.

The JSON files beside this module are a lock on the numbers the study publishes.
They were captured before the directory was refactored, so a refactor that moves
a physics number shows up as a test failure instead of as a quiet change in a
figure.

`cases.py` holds the exact commands. `capture.py` runs them and writes the JSON.
`../test_golden_regression.py` re-runs them and compares.
"""
