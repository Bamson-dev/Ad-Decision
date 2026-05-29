# Adley - AI Media Buyer (Telegram)

Built by **Bamidele Matthew**.

Telegram bot for Meta ads: conversational guidance and CSV/XLSX report analysis (pause / scale / fix).

[Launch @Addecisionbot](https://t.me/Addecisionbot)

## Features

- Meta ads chat (strategy, copy, audiences, scaling)
- CSV/XLSX report upload and DeepSeek-powered analysis
- Currency detection and spend/date thresholds
- Persistent per-user memory (last 20 messages + last report)
- **Docker / Coolify / VPS** deployment (no PaaS lock-in)

## Quick start (local)

```bash
cp .env.example .env
# Edit .env with TELEGRAM_BOT_TOKEN and DEEPSEEK_API_KEY

pip install -r requirements.txt
python main.py
```

Data is stored in `./data/users.json` by default.

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Persistent data is stored in the `adley-data` volume at `/data` inside the container.

## Production deployment

**Target:** Contabo VPS + [Coolify](https://coolify.io) + Docker + persistent volumes.

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for full Coolify setup, volumes, health checks, scaling rules, and future PostgreSQL/Redis wiring.

## Commands

- `/start` — Intro
- `/help` — Meta export steps
- `/reset` — Clear chat history (keeps last report context)

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot token from [@BotFather](https://t.me/BotFather) |
| `DEEPSEEK_API_KEY` | Yes | — | DeepSeek API key |
| `ADLEY_DATA_DIR` | No | `./data` (local), `/data` (Docker) | Directory for `users.json` |
| `LOG_LEVEL` | No | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `STORAGE_BACKEND` | No | `json` | Storage driver (`json` only today) |
| `DATABASE_URL` | No | — | Reserved for future Postgres |
| `REDIS_URL` | No | — | Reserved for future Redis |

## Requirements

- Python 3.12+ (local) or Docker image `python:3.12-slim`
