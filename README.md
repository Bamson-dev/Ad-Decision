<<<<<<< HEAD
# Ad Decision Bot

A Telegram bot that reads Meta ad report files (`.csv` or `.xlsx`) and returns clear optimization decisions using DeepSeek.

## What it does

- Supports `/start` and `/help`
- Accepts CSV and Excel reports
- Rejects files over 20MB
- Detects report currency and applies minimum spend checks
- Checks date range when date columns are available
- Calls DeepSeek only when data is sufficient
- Splits long replies into Telegram-safe message chunks

## Requirements

- Python 3.12

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create your env file:

```bash
cp .env.example .env
```

3. Edit `.env` and add your real keys:
=======
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
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31

- `TELEGRAM_BOT_TOKEN`
- `DEEPSEEK_API_KEY`

<<<<<<< HEAD
4. Run the bot:
=======
Optional:

- `ADLEY_DATA_DIR` — absolute path to the directory that should contain `users.json` (default: `/app/data` when `/app` exists, else `./data` next to `main.py`).

## Run
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31

```bash
python main.py
```

<<<<<<< HEAD
## Usage

- Send `/start` to see a quick intro.
- Send `/help` to get step-by-step Meta export instructions.
- Send your ad report file as a Telegram document (`.csv` or `.xlsx`).
=======
## Commands

- `/start` — Adley intro
- `/help` — Meta Ads Manager export steps
- `/reset` — clears conversation history; **keeps** the last report analysis in context
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
