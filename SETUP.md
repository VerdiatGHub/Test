# SETUP — Versus Incident (Windows)

This guide gets the **Versus Incident** server running fully on a Windows laptop
after `git clone`, including the AI agent (detect mode), Redis-backed on-call,
and an optional **9Router** LLM gateway in front of Gemini.

The build in this repo includes local patches on top of upstream Versus:

- A generic **`webhook` on-call provider** (`pkg/common/webhook_oncall.go`) so
  escalation can post to any HTTP endpoint — no PagerDuty/AWS account needed.
- A **`REDIS_NO_TLS`** option so on-call works against a plain local Redis.
- A configurable **AI base URL** (`AGENT_AI_BASE_URL`) so the agent can route
  through any OpenAI-compatible endpoint (9Router, OpenRouter, a local mock…).

---

## 1. Prerequisites

Install these once (winget commands shown; installers also fine):

| Tool   | Version    | Install |
|--------|------------|---------|
| Go     | 1.25+      | `winget install GoLang.Go` |
| Node   | 20 LTS+    | `winget install OpenJS.NodeJS.LTS` |
| Git    | any        | `winget install Git.Git` |
| Python | 3.10+      | `winget install Python.Python.3.12` (only for the optional mock LLM / webhook receiver helpers) |

Open a **new** PowerShell window after installing so `go`, `node`, `npm`,
`git` and `python` are on `PATH`. Verify:

```powershell
go version ; node -v ; npm -v ; git --version
```

You also need **Redis** (required for the on-call feature). Two easy options:

- **Memurai** (native Windows Redis): `winget install Memurai.MemuraiDeveloper`
- **Docker**: `docker run -d -p 6379:6379 redis:7`
- Or the Microsoft archived Redis build (Redis 5) — works with `REDIS_NO_TLS=true`.

Confirm Redis answers:

```powershell
redis-cli ping   # -> PONG   (Memurai ships memurai-cli)
```

---

## 2. Clone

```powershell
git clone https://github.com/VerdiatGHub/Test.git versus
cd versus
```

---

## 3. Build the dashboard UI

The React/Vite dashboard is embedded into the Go binary via `go:embed`, so it
must be built **first**.

```powershell
cd ui
npm install
npm run build      # outputs ui/dist, which the Go build embeds
cd ..
```

---

## 4. Build the server binary

```powershell
go build -o versus-full.exe ./cmd
```

This produces `versus-full.exe` in the repo root with the UI embedded.

---

## 5. Configuration

Defaults live in `config/config.yaml`; the AI agent log sources live in
`config/agent_sources.yaml`. The settings most relevant here are already set:

- `oncall.provider: webhook` with `oncall.webhook.url: http://127.0.0.1:9000/oncall`
- `oncall.initialized_only: true` (on-call initializes; escalation triggers when
  a finding/alert sets `oncall_enable=true`)
- `redis.host/port/password` read from env (`REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`)

Most runtime behavior is driven by environment variables (see next section), so
you usually do not need to edit the YAML.

---

## 6. Run

A ready-made launcher is included — **`run-versus.ps1`**:

```powershell
$env:GATEWAY_SECRET   = "localdemo"          # admin/API secret (X-Gateway-Secret header)
$env:AGENT_ENABLE     = "true"
$env:AGENT_MODE       = "detect"             # training | shadow | detect
$env:AGENT_NEW_SERVICE_GRACE = "0"           # 0 = no learning grace window (alert immediately)
$env:AGENT_AI_ENABLE  = "true"
$env:AGENT_AI_BASE_URL= "http://127.0.0.1:8787/v1"   # OpenAI-compatible endpoint
$env:AGENT_AI_API_KEY = "mock-key"
$env:AGENT_AI_MODEL   = "gemini-2.0-flash"
$env:REDIS_HOST       = "127.0.0.1"
$env:REDIS_PORT       = "6379"
$env:REDIS_PASSWORD   = ""
$env:REDIS_NO_TLS     = "true"               # use plaintext Redis (local dev)
$env:LARK_WEBHOOK_URL = "http://127.0.0.1:9000/lark"  # optional notify channel
.\versus-full.exe
```

Just run it:

```powershell
.\run-versus.ps1
```

The server listens on **http://127.0.0.1:3000**. Sign in to the dashboard with
the `GATEWAY_SECRET` value (`localdemo` above).

### Quick smoke test

```powershell
# health
curl http://127.0.0.1:3000/healthz

# create an incident
curl -X POST http://127.0.0.1:3000/api/incidents -H "Content-Type: application/json" -d '{"title":"test","severity":"high"}'

# list (admin)
curl http://127.0.0.1:3000/api/admin/incidents -H "X-Gateway-Secret: localdemo"
```

---

## 7. Optional helpers (zero-credential demo)

Two small Python scripts are included so you can exercise the full pipeline
without any external accounts:

- **`mock_llm.py`** — an OpenAI-compatible endpoint on `:8787` that returns a
  fixed high-severity detect verdict. Point `AGENT_AI_BASE_URL` at it.
- **`webhook_receiver.py`** — logs any POST (Lark notifications on `/lark`,
  on-call escalations on `/oncall`) to `webhook_received.log` and returns 200.

```powershell
python mock_llm.py          # http://127.0.0.1:8787/v1
python webhook_receiver.py  # http://127.0.0.1:9000
```

Start these **before** `run-versus.ps1` if you want a self-contained demo.

To see the agent auto-create an incident: append a burst of a new error type to
the file the agent watches (see `config/agent_sources.yaml`, default
`local/resource/noisy-app.log`) and wait one poll interval (~30s). The agent
mines the pattern, calls the LLM, creates an incident, sends notifications, and
escalates on-call to the webhook receiver.

---

## 8. Optional: route AI through 9Router → Gemini (real LLM)

[9Router](https://github.com/decolua/9router) is a local AI gateway that exposes
an OpenAI-compatible `/v1` endpoint and forwards to providers like Gemini.

1. Clone and run 9Router (Next.js app):
   ```powershell
   git clone https://github.com/decolua/9router.git
   cd 9router
   # create .env (set a PORT, e.g. 20128, and INITIAL_PASSWORD)
   npm install
   npm run build
   node .next/standalone/server.js   # serves the dashboard + /v1
   ```
2. Open the 9Router dashboard, log in, go to **Providers → Gemini**, and paste
   your Gemini API key.
3. Point Versus at it:
   ```powershell
   $env:AGENT_AI_BASE_URL = "http://127.0.0.1:20128/v1"
   $env:AGENT_AI_API_KEY  = "<a 9router key>"
   $env:AGENT_AI_MODEL    = "gemini-2.0-flash"
   ```

> **Gemini key note:** newer Google keys that start with `AQ.` must be sent as a
> **Bearer token** (`Authorization: Bearer <key>`), *not* via the `?key=` query
> parameter. If a key returns `400 API_KEY_INVALID` via `?key=` but works with a
> Bearer header, that's why.
>
> **Quota note:** a key can authenticate but still return `429` with `limit: 0`
> on Gemini's free tier. Enable billing on the key's Google Cloud project (or use
> a project with quota) to run real completions. Until then, use `mock_llm.py`.

---

## 9. Startup order (summary)

1. Redis (`redis-cli ping` -> PONG)
2. (optional) `python mock_llm.py` and `python webhook_receiver.py`
3. `.\run-versus.ps1`  ->  http://127.0.0.1:3000

---

## Troubleshooting

- **`package unsafe is not in std` on `go build`** — a stale `GOROOT`. Clear it:
  `go env -u GOROOT` then rebuild.
- **Server starts on :3000 ignoring config** — confirm you ran `versus-full.exe`
  from the repo root so it finds `config/`.
- **On-call panic / "context deadline exceeded" on Redis** — Redis isn't
  reachable or is speaking TLS. Start Redis and set `REDIS_NO_TLS=true` for a
  plain local instance.
- **Dashboard shows a placeholder** — the UI wasn't built; run step 3 then
  rebuild the binary (step 4).
- **`429` / `limit: 0` from Gemini** — quota; see the note in section 8.
