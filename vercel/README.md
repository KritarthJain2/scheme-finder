# Vercel deployment variant

Vercel does not run the long-lived `server.py` directly, so this folder is
the serverless version of the same real-data logic that is actually deployed
at https://scheme-finder-kritarthjain1968-gmailcoms-projects.vercel.app

- `index.html` — same UI as `../public/index.html`
- `api/find.py` — Tavily search + Nemotron ranking over Tavily results only
- `api/status.py` — reports whether Tavily / Nebius keys are configured

Keys are read only from Vercel environment variables (`TAVILY_API_KEY`,
`NEBIUS_API_KEY`, `NEBIUS_MODEL`). No key is stored in this repo.
