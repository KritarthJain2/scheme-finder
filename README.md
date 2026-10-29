# Scheme Finder — REAL DATA ONLY

**Nebius x NVIDIA Global AI Hackathon — Best Apps & Agents track**

## Live demo

- Demo URL: https://scheme-finder-kritarthjain1968-gmailcoms-projects.vercel.app
- Deployed code: see `vercel/` in this repo (Vercel does not run the
  long-lived `server.py` directly, so `vercel/` is the serverless version
  of the same logic).
- Live status, checked 2026-10-29: `/api/status` reports
  `tavily_configured: true`, `nebius_configured: false`, `mode: real`.
  That means the live demo currently runs in search-only mode: real
  Tavily results, with Nemotron AI matching OFF until a Nebius Token
  Factory key is set. Search-only mode is NOT a live-Nemotron submission
  claim — see "Hackathon compliance" below.

A simple Hindi/English web app that searches real, current government
scheme pages and shows only what the search actually found, with the
official link to verify on.

It is guidance only — never approval. The app never asks for a name,
Aadhaar number, phone number, or bank details, and it stores nothing.

## What was removed, and why

The old demo mode and the old curated scheme list are gone, by design:

- No `data/schemes.json` any more.
- No "Browse all schemes" section any more — there is no list to browse
  without a real search.
- No rule-match, no fallback scheme, and no invented benefit, document,
  or link anywhere in the code.

If real search fails, or no key is set, the app shows an error or an
empty result — it does not fill the page with a made-up scheme.

## How it works now

1. The user fills a short, anonymous profile: age (optional), state,
   occupation, income band, and a free-text description.
2. The server searches Tavily for current schemes, restricted to
   `gov.in`, `india.gov.in`, and `myscheme.gov.in`. This is the only
   source of scheme names and links.
3. If `NEBIUS_API_KEY` is set, a NVIDIA Nemotron model on Nebius Token
   Factory (OpenAI-compatible API at
   `https://api.tokenfactory.nebius.com/v1`) ranks and explains ONLY
   those Tavily results. The server drops any Nemotron match whose URL
   is not exactly a Tavily result URL, so the model cannot invent a
   scheme or a link.
4. Without a Nebius key, Tavily results are shown as-is, labelled
   "search only, AI matching off". They are still real search results.

## Why Tavily, not a direct myScheme API

myScheme has no public, key-free developer API for third-party apps.
Its official API route is through API Setu, which requires
registration/subscription, and its website frontend uses a private
backend path with a rotating client key and a 401 guard. This project
does not use that private path. Tavily, with a key from the Nebius
Builder Program, is the legitimate real-data search route used here.

## Run it

A Tavily key is now REQUIRED for any result:

```bash
export TAVILY_API_KEY="your-tavily-key"
export NEBIUS_API_KEY="your-nebius-token-factory-key"
export NEBIUS_MODEL="nvidia/nemotron-3-nano-omni"  # verify in the Token Factory catalogue
python3 server.py
# open http://localhost:8000
```

Without `TAVILY_API_KEY`, `/api/find` returns 503 by design and shows
no schemes. Without `NEBIUS_API_KEY`, results are search-only.

See `.env.example` for the full list. No dependencies: Python 3.10+
standard library only. Keys are server-side only, never in the browser.

## What was tested here, and what was not

- **Tested here:** server starts, `/api/status` reports real search
  as not-configured with no keys, and `POST /api/find` returns 503
  with no schemes — proving the old fallback is gone. See `TESTING.md`.
- **Tested live (deployed site, search-only):** with a Tavily key set
  on Vercel, real form searches returned real `gov.in` results with no
  error (verified 2026-10-28, and `/api/status` rechecked 2026-10-29).
- **Not tested here:** a real Nemotron match, because no Nebius key
  has been set. That path is implemented in `server.py`
  (`tavily_search` and `nemotron_match`) and in `vercel/api/find.py`,
  but needs a Nebius key and a check of the exact model ID in the
  Token Factory catalogue before a live-mode submission claim.
- **Not yet done for Devpost:** record a ≤3-minute video of the real
  app working, and submit on Devpost with this repo, a README like
  this one, and feedback on Token Factory / Nemotron. The public demo
  URL above already works for judges.

## Hackathon compliance

- Runs on Nebius Token Factory in live mode and uses at least one
  NVIDIA open model (Nemotron). Search-only mode is NOT a submission
  claim — the submission must be tested in live mode first.
- Uses Tavily for current scheme information (live mode), which is
  the basis for the Best Use of Tavily prize.
- Public repo + MIT license + setup instructions (this file).
- Feedback for Nebius / NVIDIA goes in the Devpost submission form,
  not in this repo.

## Privacy and limits

- No personal identifiers are collected. Age, state, occupation, income
  band, and description are used only for that one request and are not
  stored. Server logs record only method + path, never profile text.
- A result is only as current as the official page it links to. The
  official page is always the correct source, and the UI says so on
  every result.
- The old phone-only single-file demo is obsolete and must not be
  used any more: opened without a server it cannot fetch real data,
  and it must not show fake schemes instead.

## Project layout

- `server.py` — stdlib-only server, Tavily real search + Nemotron
  ranking over search results only, no curated fallback
- `public/index.html` — mobile-first UI, English/Hindi toggle, no
  embedded scheme data
- `vercel/` — serverless deployment variant actually running at the
  demo URL above (`vercel/api/find.py`, `vercel/api/status.py`)
- `TESTING.md` — how the no-fallback test was run, with exact commands
