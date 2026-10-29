#!/usr/bin/env python3
"""
Scheme Finder — REAL DATA ONLY — Nebius x NVIDIA Global AI Hackathon
(Best Apps & Agents track)

What changed in this version
----------------------------
The old demo mode and the old curated list are REMOVED, on purpose.
There is no fallback list, no rule-match, and no invented scheme,
benefit amount, document list, or link anywhere in this code.

How a result is produced, in order
----------------------------------
1. The user fills a short, anonymous profile: age, state, occupation,
   income band, and a free-text description. No name, Aadhaar number,
   phone number, bank details, or documents are collected, and nothing
   is stored.
2. The server MUST search Tavily for current government schemes
   (POST https://api.tavily.com/search), restricted to gov.in,
   india.gov.in, and myscheme.gov.in. This is the only source of
   scheme names and links. Without TAVILY_API_KEY the request fails
   honestly with 503 — it does not fall back to any list.
3. If NEBIUS_API_KEY is set, a NVIDIA Nemotron model on Nebius Token
   Factory (OpenAI-compatible API, base
   https://api.tokenfactory.nebius.com/v1) ranks and explains ONLY the
   Tavily results. The server then drops any Nemotron match whose URL
   is not exactly one of the Tavily result URLs, so the model cannot
   invent a scheme or a link.
4. If no Nebius key is set, the Tavily results are shown as-is,
   labelled "search only, AI matching off". They are still real
   search results, not curated data.

Why Tavily, and why not a direct myScheme API
--------------------------------------------
myScheme has no public, key-free developer API for third-party apps:
its official API route is through API Setu, which requires
registration/subscription, and its website frontend uses a private
backend path with a rotating client key and a 401 guard. This project
does not use that private path. Tavily, with a key from the Nebius
Builder Program, is the legitimate real-data search route used here.

Security notes
--------------
* API keys are read ONLY from environment variables on the server.
  They are never sent to the browser, never logged, and never committed.
  See .env.example — it contains no real keys.
* The frontend only calls POST /api/find on this same server.
* The server is stateless: it does not write a database and does not
  keep profiles after the request ends.

Run:
    TAVILY_API_KEY=... NEBIUS_API_KEY=... python3 server.py
    # then open http://localhost:8000
    # without TAVILY_API_KEY, /api/find returns 503 by design.

Env vars:
    PORT                 default 8000
    TAVILY_API_KEY       REQUIRED for any real result
    NEBIUS_API_KEY       required for the Token Factory / Nemotron
                         submission claim; without it, results are
                         search-only
    NEBIUS_MODEL         default nvidia/nemotron-3-nano-omni
                         (verify the exact ID in the Token Factory
                         catalogue before submitting — model IDs change)
    NEBIUS_BASE_URL      default https://api.tokenfactory.nebius.com/v1
"""

import json
import os
import re
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
PUBLIC = BASE / "public"

NEBIUS_BASE = os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1").rstrip("/")
NEBIUS_MODEL = os.environ.get("NEBIUS_MODEL", "nvidia/nemotron-3-nano-omni")
NEBIUS_KEY = os.environ.get("NEBIUS_API_KEY", "")
TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")


def _post_json(url, payload, headers, timeout=30):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class SearchNotConfigured(Exception):
    pass


class SearchFailed(Exception):
    pass


def tavily_search(profile, lang):
    """Real search only. Raises SearchNotConfigured / SearchFailed.

    Returns a list of {title, url, content} taken verbatim from Tavily.
    Never returns curated or invented entries.
    """
    if not TAVILY_KEY:
        raise SearchNotConfigured("TAVILY_API_KEY is not set on the server")
    query = (
        f"government scheme India {profile.get('occupation', '')} "
        f"{profile.get('state', '')} {profile.get('description', '')}".strip()
    )
    try:
        data = _post_json(
            "https://api.tavily.com/search",
            {
                "query": query,
                "search_depth": "basic",
                "max_results": 10,
                "include_domains": ["gov.in", "india.gov.in", "myscheme.gov.in"],
            },
            {"Authorization": f"Bearer {TAVILY_KEY}"},
            timeout=20,
        )
    except Exception as exc:
        raise SearchFailed(f"Tavily search failed: {type(exc).__name__}") from exc
    out = []
    for r in data.get("results", []) or []:
        if r.get("url"):
            out.append(
                {
                    "title": r.get("title", "") or "",
                    "url": r.get("url", ""),
                    "content": (r.get("content", "") or "")[:800],
                }
            )
    return out


def nemotron_match(profile, search_results, lang):
    """Ask Nemotron to rank ONLY the Tavily results. Return dict or None.

    Any returned match whose URL is not exactly a Tavily URL is dropped.
    Documents are kept only if the model lists them; an empty list means
    'not stated in the source — check the official page', not a guess.
    """
    if not NEBIUS_KEY:
        return None
    lang_name = "Hindi, in simple words" if lang == "hi" else "simple English"
    system = (
        "You rank Indian government schemes for a person's profile. "
        "Use ONLY the search results given to you. Reply with JSON ONLY, "
        "no other text. Shape: "
        '{"matches": [{"name": "<exact title from a search result>", '
        '"url": "<exact url from that same search result>", '
        '"why": "...", "documents": ["..."], "next_step": "...", '
        '"confidence": "high|medium|low"}], '
        '"disclaimer": "This is guidance only, not approval. Always verify on the official page linked."} '
        "NEVER invent a scheme, benefit amount, document, or link. "
        "NEVER use a URL that is not in the search results. "
        "If a benefit or document is not stated in the search result, "
        "leave it out and say to check the official page. "
        "Do not ask for Aadhaar, bank, or phone details."
    )
    user = json.dumps(
        {"profile": profile, "language": lang_name, "tavily_results": search_results},
        ensure_ascii=False,
    )
    try:
        data = _post_json(
            f"{NEBIUS_BASE}/chat/completions",
            {
                "model": NEBIUS_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.2,
                "max_tokens": 2000,
            },
            {"Authorization": f"Bearer {NEBIUS_KEY}"},
            timeout=45,
        )
    except Exception:
        return None
    try:
        text = data["choices"][0]["message"]["content"]
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
        parsed = json.loads(text)
        if not isinstance(parsed.get("matches"), list):
            return None
    except Exception:
        return None
    allowed_urls = {r["url"] for r in search_results}
    kept = []
    for m in parsed["matches"]:
        if not isinstance(m, dict):
            continue
        if m.get("url") not in allowed_urls:
            continue  # invented or mismatched link — drop it, never show it
        kept.append(
            {
                "name": str(m.get("name", ""))[:200],
                "url": m["url"],
                "why": str(m.get("why", ""))[:500],
                "documents": [str(d)[:200] for d in (m.get("documents") or [])][:10],
                "next_step": str(m.get("next_step", "Verify on the linked official page."))[:300],
                "confidence": m.get("confidence") if m.get("confidence") in ("high", "medium", "low") else "low",
                "official": m["url"],
            }
        )
    if not kept:
        return None
    parsed["matches"] = kept[:5]
    return parsed


def search_only_matches(search_results):
    """Turn Tavily results into matches without adding any new facts."""
    matches = []
    for r in search_results[:5]:
        matches.append(
            {
                "name": r["title"] or r["url"],
                "url": r["url"],
                "why": (r["content"][:300] if r["content"] else "Found by real search on an official government domain."),
                "documents": [],
                "next_step": "Open the linked official page and check eligibility, documents, and dates there.",
                "confidence": "low",
                "official": r["url"],
            }
        )
    return {
        "matches": matches,
        "disclaimer": "Search only: these are real Tavily search results from official "
        "government domains. AI matching is off (no Nebius key). This is "
        "guidance only, not approval. Always verify on the linked official page.",
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def log_message(self, *args):
        # Keep logs free of profile details: only method + path.
        print(f"{self.command} {urlparse(self.path).path}")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path != "/api/find":
            return self._send_json({"error": "Not found"}, 404)
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        raw = self.rfile.read(min(length, 100_000)) if length else b"{}"
        try:
            profile = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._send_json({"error": "Invalid JSON"}, 400)
        profile = {
            "age": profile.get("age"),
            "state": str(profile.get("state", ""))[:60],
            "occupation": str(profile.get("occupation", ""))[:60],
            "income": str(profile.get("income", ""))[:20],
            "description": str(profile.get("description", ""))[:500],
            "language": "hi" if profile.get("language") == "hi" else "en",
        }
        if isinstance(profile["age"], str):
            try:
                profile["age"] = int(profile["age"])
            except ValueError:
                profile["age"] = None
        lang = profile["language"]
        try:
            search_results = tavily_search(profile, lang)
        except SearchNotConfigured:
            return self._send_json(
                {
                    "error": "tavily_not_configured",
                    "message": "Real search is not configured: TAVILY_API_KEY is missing on the server. "
                    "No schemes are shown, because there is no curated fallback any more.",
                },
                503,
            )
        except SearchFailed as exc:
            return self._send_json(
                {
                    "error": "search_failed",
                    "message": f"Real search failed ({exc}). No schemes are shown, because there is no curated fallback any more.",
                },
                502,
            )
        if not search_results:
            return self._send_json(
                {
                    "matches": [],
                    "disclaimer": "Real search ran, but found no scheme on an official government domain for this profile. Try different words, or check the official finder directly.",
                    "mode": "real-empty",
                    "model": None,
                    "sources": [],
                    "live_search": True,
                }
            )
        live = nemotron_match(profile, search_results, lang) if NEBIUS_KEY else None
        if live is not None:
            mode = "live"
            result = live
        else:
            mode = "search-only"
            result = search_only_matches(search_results)
        result["mode"] = mode
        result["model"] = NEBIUS_MODEL if mode == "live" else None
        result["sources"] = search_results
        result["live_search"] = True
        return self._send_json(result)

    def do_GET(self):
        # /api/status is safe: it reports only whether keys are configured,
        # never the keys themselves.
        if urlparse(self.path).path == "/api/status":
            return self._send_json(
                {
                    "nebius_configured": bool(NEBIUS_KEY),
                    "tavily_configured": bool(TAVILY_KEY),
                    "model": NEBIUS_MODEL,
                    "mode": "real" if TAVILY_KEY else "not-configured",
                }
            )
        return super().do_GET()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Scheme Finder (real data only) on http://localhost:{port}  (nebius={'yes' if NEBIUS_KEY else 'no'}, tavily={'yes' if TAVILY_KEY else 'no'})")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
