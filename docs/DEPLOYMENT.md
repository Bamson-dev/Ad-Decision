# Deployment: Contabo VPS + Coolify + Docker

This application is a **long-running Telegram polling worker**. It does not serve HTTP traffic. Deploy it on Coolify as a **Dockerfile-based application** with a **persistent volume** — not as a public web service.

## Architecture

```
Contabo VPS
└── Coolify
    ├── adley (Docker)     ← this repo, TELEGRAM_BOT_TOKEN, DEEPSEEK_API_KEY
    │   └── volume → /data/users.json
    ├── postgres (future)  ← DATABASE_URL
    └── redis (future)     ← REDIS_URL
```

## 1. Coolify application setup

1. In Coolify, **+ Add Resource** → **Application** → your Git repo (`Bamson-dev/Ad-Decision`).
2. **Build pack:** Dockerfile (path: `/Dockerfile`).
3. **Do not** expose a public HTTP port for this app (no `PORT` binding required).
4. **Replicas:** `1` only — Telegram long polling allows one active poller per bot token.

## 2. Environment variables

Set in Coolify → your service → **Environment**:

| Variable | Value |
|----------|--------|
| `TELEGRAM_BOT_TOKEN` | From BotFather (mark secret) |
| `DEEPSEEK_API_KEY` | From DeepSeek (mark secret) |
| `ADLEY_DATA_DIR` | `/data` |
| `LOG_LEVEL` | `INFO` (or `DEBUG` while testing) |
| `STORAGE_BACKEND` | `json` |

Coolify injects these at container start. You do **not** need a `.env` file inside the image.

## 3. Persistent storage (required)

User memory lives in `users.json`. Without a volume, data is lost on every redeploy.

1. Coolify → your application → **Storages** (or Persistent Storage).
2. Add a volume:
   - **Mount path (container):** `/data`
   - **Size:** 1 GB is enough for v1
3. Ensure `ADLEY_DATA_DIR=/data` is set.

On first start the entrypoint creates `/data` and an empty `users.json` if missing.

## 4. Health checks

The Dockerfile defines a `HEALTHCHECK` that:

- Verifies `/data` is writable
- Calls Telegram `getMe` to confirm the token works

In Coolify, enable **Use Dockerfile HEALTHCHECK** if offered, or leave default Docker behavior. Do not configure HTTP health checks on a port.

## 5. Logs

Logging goes to **stdout** (`PYTHONUNBUFFERED=1`). View logs in Coolify → **Logs**. Format:

```
2026-05-29 12:00:00 INFO [__main__] Adley starting (data_dir=/data, ...)
```

## 6. Graceful shutdown

The image uses **tini** as PID 1 and python-telegram-bot handles **SIGTERM** on container stop/redeploy. Coolify rolling updates should send SIGTERM before SIGKILL.

## 7. Internal services (PostgreSQL / Redis)

When you add Postgres or Redis as separate Coolify resources on the same server:

1. Use Coolify **internal hostnames** (service name), e.g. `postgres`, `redis`.
2. Add env vars to the Adley app:

```env
DATABASE_URL=postgresql://adley:YOUR_PASSWORD@postgres:5432/adley
REDIS_URL=redis://redis:6379/0
```

3. Link services in Coolify’s network so the bot container can resolve those hostnames.
4. Postgres/Redis storage in code is **not implemented yet** — `STORAGE_BACKEND=json` remains the active backend until a migration ships.

## 8. Build & deploy locally (test before Coolify)

```bash
cp .env.example .env
docker compose up --build
docker compose logs -f adley
```

## 9. Migrating existing `users.json`

Copy your file into the mounted volume (one-time):

```bash
# On the VPS, after first deploy with volume attached
docker cp ./users.json <container_id>:/data/users.json
docker exec -u adley <container_id> chmod 644 /data/users.json
```

Or use Coolify’s file manager / shell if available.

## 10. Production checklist

- [ ] Only **one** replica / container for this bot token
- [ ] Volume mounted at `/data`
- [ ] Secrets set in Coolify (not committed to Git)
- [ ] Old hosts (Render/Railway) **stopped** to avoid `409 Conflict` on polling
- [ ] Token rotated if it ever appeared in public logs
- [ ] Contabo firewall: outbound HTTPS allowed (Telegram + DeepSeek APIs)
- [ ] Optional: backup `/data/users.json` on a schedule

## 11. Scaling notes

| Goal | Approach |
|------|----------|
| Single bot, more CPU | Increase VPS / container resources |
| Multiple bots | One container per `TELEGRAM_BOT_TOKEN` |
| Horizontal scale (same bot) | Requires **webhook** mode + shared DB — not implemented |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `409 Conflict` on getUpdates | Stop duplicate containers or old Railway/Render instances |
| Empty memory after redeploy | Attach persistent volume at `/data` |
| `TELEGRAM_BOT_TOKEN is missing` | Set env var in Coolify and redeploy |
| Health check failing | Check token validity and volume permissions |
| Report analysis timeout | Increase `DEEPSEEK_TIMEOUT_SECONDS` (max 90+ in code) |

## Removed platform assumptions

This repo no longer includes Render Blueprint (`render.yaml`), Railway paths (`/app/data`), or Render filesystem paths (`/opt/render/project/src`). Deployment is **Docker-first** for Coolify on your VPS.
