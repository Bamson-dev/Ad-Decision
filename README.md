# Adley — AI media buyer (Telegram)

**Author:** Bamidele Matthew

Adley is a Telegram bot that acts as a senior **Meta ads** media buyer: free-form chat about ads, copy, audiences, creatives, and scaling, plus **CSV / Excel** report uploads at any time for structured analysis (pause / scale / fix).

## Features

- **Conversational mode** — ask anything ad-related; off-topic questions get a short redirect.
- **Report uploads** — mid-conversation; currency detection (headers + spend-cell symbols), spend and date thresholds before calling the model.
- **Persistent memory (v1)** — last **20** messages per user, plus last report summary, full last analysis, and detected currency, stored in **`/app/data/users.json`** on Railway (or under `./data` locally unless `ADLEY_DATA_DIR` is set).

### Railway memory across deploys

On the default Railway filesystem, **`/app/data` is ephemeral** — each redeploy can reset `users.json`. That is acceptable for v1.

To keep memory across deployments:

1. In the Railway service, add a **persistent volume** mounted at **`/app/data`** (or another path and set **`ADLEY_DATA_DIR`** to that path).
2. Redeploy so the app writes `users.json` on the mounted volume.

## Requirements

- Python **3.9+** (tested through 3.13 on hosts like Railpack)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- `TELEGRAM_BOT_TOKEN`
- `DEEPSEEK_API_KEY`

Optional:

- `ADLEY_DATA_DIR` — absolute path to the directory that should contain `users.json` (default: `/app/data` when `/app` exists, else `./data` next to `main.py`).

## Run

```bash
python main.py
```

## Commands

- `/start` — Adley intro
- `/help` — Meta Ads Manager export steps
- `/reset` — clears conversation history; **keeps** the last report analysis in context
