#!/bin/sh
# Run Scheme Finder. No dependencies beyond Python 3.10+.
# Set TAVILY_API_KEY (required) and NEBIUS_API_KEY in the environment.
# Without TAVILY_API_KEY, /api/find returns 503 by design — no demo fallback.
exec python3 "$(dirname "$0")/server.py"
