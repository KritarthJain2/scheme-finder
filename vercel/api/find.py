"""Vercel serverless version of Scheme Finder /api/find — REAL DATA ONLY.

Same logic as scheme-finder/server.py, adapted for Vercel's Python
runtime (BaseHTTPRequestHandler, class name `handler`). No curated
list, no demo fallback. Without TAVILY_API_KEY this returns 503.
If Nemotron times out or fails, results fall back to search-only
(real Tavily results), never to invented schemes.
"""
import json
import os
import re
import urllib.request
from http.server import BaseHTTPRequestHandler

NEBIUS_BASE = os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1").rstrip("/")
NEBIUS_MODEL = os.environ.get("NEBIUS_MODEL", "nvidia/nemotron-3-nano-omni")
NEBIUS_KEY = os.environ.get("NEBIUS_API_KEY", "")
TAVILY_KEY = os.environ.get("TAVILY_API_KEY", "")


def _post_json(url, payload, headers, timeout=15):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class SearchNotConfigured(Exception):
    pass


class SearchFailed(Exception):
    pass


def tavily_search(profile):
    if not TAVILY_KEY:
        raise SearchNotConfigured("TAVILY_API_KEY is not set")
    query = f"government scheme India {profile.get('occupation', '')} {profile.get('state', '')} {profile.get('description', '')}".strip()
    try:
        data = _post_json(
            "https://api.tavily.com/search",
            {"query": query, "search_depth": "basic", "max_results": 10,
             "include_domains": ["gov.in", "india.gov.in", "myscheme.gov.in"]},
            {"Authorization": f"Bearer {TAVILY_KEY}"}, timeout=10,
        )
    except Exception as exc:
        raise SearchFailed(type(exc).__name__) from exc
    out = []
    for r in data.get("results", []) or []:
        if r.get("url"):
            out.append({"title": r.get("title", "") or "", "url": r.get("url", ""),
                        "content": (r.get("content", "") or "")[:800]})
    return out


def nemotron_match(profile, search_results, lang):
    if not NEBIUS_KEY:
        return None
    lang_name = "Hindi, in simple words" if lang == "hi" else "simple English"
    system = (
        "You rank Indian government schemes for a person's profile. "
        "Use ONLY the search results given to you. Reply with JSON ONLY. "
        'Shape: {"matches": [{"name": "<exact title from a search result>", '
        '"url": "<exact url from that same search result>", "why": "...", '
        '"documents": ["..."], "next_step": "...", '
        '"confidence": "high|medium|low"}], '
        '"disclaimer": "This is guidance only, not approval. Always verify on the official page linked."} '
        "NEVER invent a scheme, benefit amount, document, or link. "
        "NEVER use a URL that is not in the search results. "
        "If a benefit or document is not stated in the search result, leave it out."
    )
    user = json.dumps({"profile": profile, "language": lang_name, "tavily_results": search_results}, ensure_ascii=False)
    try:
        data = _post_json(
            f"{NEBIUS_BASE}/chat/completions",
            {"model": NEBIUS_MODEL,
             "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
             "temperature": 0.2, "max_tokens": 2000},
            {"Authorization": f"Bearer {NEBIUS_KEY}"}, timeout=25,
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
    allowed = {r["url"] for r in search_results}
    kept = []
    for m in parsed["matches"]:
        if not isinstance(m, dict) or m.get("url") not in allowed:
            continue
        kept.append({
            "name": str(m.get("name", ""))[:200], "url": m["url"],
            "why": str(m.get("why", ""))[:500],
            "documents": [str(d)[:200] for d in (m.get("documents") or [])][:10],
            "next_step": str(m.get("next_step", "Verify on the linked official page."))[:300],
            "confidence": m.get("confidence") if m.get("confidence") in ("high", "medium", "low") else "low",
            "official": m["url"],
        })
    if not kept:
        return None
    parsed["matches"] = kept[:5]
    return parsed


def search_only_matches(search_results):
    return {
        "matches": [{
            "name": r["title"] or r["url"], "url": r["url"],
            "why": (r["content"][:300] if r["content"] else "Found by real search on an official government domain."),
            "documents": [],
            "next_step": "Open the linked official page and check eligibility, documents, and dates there.",
            "confidence": "low", "official": r["url"],
        } for r in search_results[:5]],
        "disclaimer": "Search only: these are real Tavily search results from official government domains. "
        "AI matching is off (no Nebius key). Guidance only, not approval. Always verify on the linked official page.",
    }


class handler(BaseHTTPRequestHandler):
    def _send(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        raw = self.rfile.read(min(length, 100_000)) if length else b"{}"
        try:
            profile_in = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return self._send({"error": "Invalid JSON"}, 400)
        profile = {
            "age": profile_in.get("age"),
            "state": str(profile_in.get("state", ""))[:60],
            "occupation": str(profile_in.get("occupation", ""))[:60],
            "income": str(profile_in.get("income", ""))[:20],
            "description": str(profile_in.get("description", ""))[:500],
            "language": "hi" if profile_in.get("language") == "hi" else "en",
        }
        if isinstance(profile["age"], str):
            try:
                profile["age"] = int(profile["age"])
            except ValueError:
                profile["age"] = None
        try:
            search_results = tavily_search(profile)
        except SearchNotConfigured:
            return self._send({
                "error": "tavily_not_configured",
                "message": "Real search is not configured: TAVILY_API_KEY is missing on the server. No schemes are shown, because there is no curated fallback any more.",
            }, 503)
        except SearchFailed as exc:
            return self._send({
                "error": "search_failed",
                "message": f"Real search failed ({exc}). No schemes are shown, because there is no curated fallback any more.",
            }, 502)
        if not search_results:
            return self._send({
                "matches": [],
                "disclaimer": "Real search ran, but found no scheme on an official government domain for this profile.",
                "mode": "real-empty", "model": None, "sources": [], "live_search": True,
            })
        live = nemotron_match(profile, search_results, profile["language"]) if NEBIUS_KEY else None
        if live is not None:
            result, mode = live, "live"
        else:
            result, mode = search_only_matches(search_results), "search-only"
        result["mode"] = mode
        result["model"] = NEBIUS_MODEL if mode == "live" else None
        result["sources"] = search_results
        result["live_search"] = True
        return self._send(result)

    def do_GET(self):
        return self._send({"error": "Use POST /api/find"}, 405)
