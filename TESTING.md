# Testing — Scheme Finder (real data only)

## No-fallback test actually run in this workspace (2026-10-27)

No API keys were set, so this test proves the old demo/curated path
is gone — it does NOT prove a real search works. A real search needs
real keys, which were not provided here.

Commands run:

```bash
cd ~/workspace/scheme-finder
python3 -m py_compile server.py
grep -R -i "demo_match\|load_schemes\|schemes.json" server.py public/index.html
# -> no matches: demo matcher and curated list are removed
grep -R -i "NEBIUS_API_KEY\|TAVILY_API_KEY" public/
# -> no keys in frontend: OK

PORT=8000 python3 server.py
curl -s http://localhost:8000/api/status
# -> {"nebius_configured": false, "tavily_configured": false,
#     "model": "nvidia/nemotron-3-nano-omni", "mode": "not-configured"}

curl -s -X POST http://localhost:8000/api/find \
  -H 'Content-Type: application/json' \
  -d '{"age":32,"state":"Uttar Pradesh","occupation":"farmer","income":"low","description":"I am a farmer with a small field.","language":"en"}'
# -> HTTP 503, error "tavily_not_configured", no matches at all

curl -s http://localhost:8000/api/schemes
# -> 404: the old curated-list endpoint is gone
```

## Still to test before Devpost submission

1. Set `NEBIUS_API_KEY` and `TAVILY_API_KEY`, verify the exact
   Nemotron model ID in the Token Factory catalogue, then run the
   same `/api/find` request and confirm `mode: live`, and confirm
   every returned URL is also in the `sources` list (the server
   already drops any URL that is not).
2. Deploy the server to a public host and confirm the demo URL loads
   on a phone and returns real results, not an error page.
3. Record a ≤3-minute video of the live app working with real keys.
   The old demo video script is obsolete — do not use its demo cases
   as if they were live results.
