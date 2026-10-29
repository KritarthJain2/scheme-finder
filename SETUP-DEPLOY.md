# Scheme Finder — Full setup, build, and deploy steps

## 1. Kya chahiye (requirements)

- Python 3.10+ (koi pip install nahi chahiye — server stdlib-only hai)
- Ek Tavily key — bina iske koi real result nahi milega, /api/find 503 dega
- Ek Nebius Token Factory key — live Nemotron ranking aur hackathon
  submission claim ke liye (bina iske results "search-only" honge)
- Keys kabhi chat me, code me, ya Git me mat daalna. Sirf server ke
  environment variables me.

Keys kahan se: Nebius Builder Program se Token Factory aur Tavily ke
credits milte hain (Devpost rules me bhi yehi likha hai). Wahan se key
banakar, neeche wale step me environment variable ki tarah set karo.

## 2. Local setup (full project, server.py wala)

```bash
# zip unzip karo, phir folder me jao
cd scheme-finder

# keys set karo (apni asli keys se replace karo, quotes ke andar)
export TAVILY_API_KEY="tumhari-tavily-key"
export NEBIUS_API_KEY="tumhari-nebius-key"
export NEBIUS_MODEL="nvidia/nemotron-3-nano-omni"
# model ID ko Token Factory catalogue me verify karna zaroori hai —
# ye default abhi verify nahi hua hai

# server chalao
python3 server.py
# open http://localhost:8000
```

## 3. Build — isme koi build step nahi hai

- Koi npm, pip, ya compile step nahi hai.
- Frontend ek hi `public/index.html` file hai, backend ek hi
  `server.py` hai. "Build" ka matlab yahan sirf ye check hai:
  `python3 -m py_compile server.py` — error nahi aana chahiye.
- Agar sirf file dekhni hai to zip hi kaafi hai, install kuch nahi.

## 4. Test karo, submit se pehle

```bash
curl -s http://localhost:8000/api/status
# chahiye: {"tavily_configured": true, "nebius_configured": true, "mode": "real"}

curl -s -X POST http://localhost:8000/api/find \
  -H 'Content-Type: application/json' \
  -d '{"age":32,"state":"Uttar Pradesh","occupation":"farmer","income":"low","description":"I am a farmer with a small field.","language":"en"}'
# chahiye: "mode": "live"
# har match ka URL "sources" list me bhi hona chahiye — server nakli
# URL wale match ko khud kaat deta hai.
```

- 503 aaye = Tavily key missing hai, koi scheme nahi dikhegi (by design).
- 502 aaye = Tavily search fail hui hai, phir bhi koi fake scheme nahi.
- Mode "search-only" aaye = Tavily chal rahi hai, Nebius key missing hai.

## 5. Site ke roop me deploy — Vercel (ye project ke liye taiyaar hai)

Important: Vercel lambi chalne wali `server.py` ko seedha nahi chalata.
Isliye Vercel ke liye alag folder banaya gaya hai:
`scheme-finder-vercel/` — isme `index.html` + `api/find.py` +
`api/status.py` hain, wahi real-data logic, serverless form me.

Vercel steps (dashboard se):

1. Vercel me project `scheme-finder` kholo.
2. Settings → Environment Variables me ye daalo:
   - `TAVILY_API_KEY` = tumhari Tavily key
   - `NEBIUS_API_KEY` = tumhari Nebius key
   - `NEBIUS_MODEL` = verified model ID
   Target: Production (aur Preview, agar chaho).
3. Deployments me jaakar latest deployment ko Redeploy karo —
   env var badalne ke baad bina redeploy ke naya key nahi lagega.
4. Settings → Deployment Protection / Vercel Authentication OFF karo,
   warna site login maangegi aur judges use nahi khol payenge.
5. Verify karo:
   - Main page bina login ke khule
   - `/api/status` me `tavily_configured: true` dikhe
   - Form se ek search karke real result aaye

Vercel note: Hobby plan par function timeout chhota hota hai. Agar
Nemotron slow ho to result "search-only" me bhi aa sakta hai — wo bhi
real Tavily result hoga, fake nahi.

## 6. Site ke roop me deploy — Render (alternative, server.py jaisa ka taisa)

Agar Vercel ke bajay Render chaho, to `server.py` me koi change nahi
chahiye:

1. Project ko public GitHub repo me daalo (MIT LICENSE ke saath).
2. Render → New → Web Service → us repo ko connect karo.
3. Build Command: khaali / koi nahi. Start Command: `python3 server.py`
4. Environment me `PORT` Render khud deta hai, aur tum
   `TAVILY_API_KEY`, `NEBIUS_API_KEY`, `NEBIUS_MODEL` daalo.
5. Deploy ke baad wahi `/api/status` aur `/api/find` test karo.
   Free tier par service idle hone par so sakti hai, pehla request
   slow ho sakta hai.

## 7. Devpost ke liye baaki checklist

- Public GitHub repo (MIT license ke saath) + README
- Public demo URL (upar wali site)
- ≤3 minute ka YouTube video — sirf live app ka, real keys ke saath
- Track: Best Apps & Agents
- Description me Nemotron + Token Factory + Tavily ka use saaf likhna
- Token Factory / Nemotron par feedback form me dena
- Deadline: Friday, 30 Oct 2026, raat 10:30 IST — usse pehle submit karo
