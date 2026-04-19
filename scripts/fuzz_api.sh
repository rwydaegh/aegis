#!/usr/bin/env bash
# Local deep Schemathesis sweep against the AEGIS viewer HTTP API.
# Starts Flask, runs the fuzzer against /api/openapi.json, tears down.
#
# Usage:
#   scripts/fuzz_api.sh                  # default 500 examples
#   scripts/fuzz_api.sh --max-examples=50  # fast smoke
#
# Additional flags are passed through to `schemathesis run`.
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-uv run python}

$PYTHON -m aegis.viewer --scenario open_ground &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null || true' EXIT

# Wait for server
for _ in {1..30}; do
    if curl -sf http://localhost:5000/api/openapi.json >/dev/null; then
        break
    fi
    sleep 1
done

if ! curl -sf http://localhost:5000/api/openapi.json >/dev/null; then
    echo "Viewer did not come up on :5000 within 30s"
    exit 1
fi

# Run the fuzzer. Excluded checks match the hotspot notes:
# - negative_data_rejection: noisy false-positive hotspot (Schemathesis #2312)
# - ignored_auth: viewer auth is gate-based not per-route (Schemathesis #2482)
# response_schema_conformance stays enabled; X-Stats-in-header responses are
# documented as binary bodies so the check validates the content-type only.
uvx schemathesis run http://localhost:5000/api/openapi.json \
    --checks=all \
    --phases=examples,fuzzing,stateful \
    --rate-limit=20/s \
    --max-examples=500 \
    --exclude-checks=negative_data_rejection,ignored_auth,unsupported_method,content_type_conformance,positive_data_acceptance \
    "$@"
