# Adley - AI Media Buyer (Telegram)

Built by **Bamidele Matthew**.

Adley is a Telegram bot for Meta ads support. It handles free-form ad strategy conversations and analyzes uploaded report files (`.csv` or `.xlsx`) to return clear optimization guidance.

## Try Adley on Telegram

[Launch @Addecisionbot](https://t.me/Addecisionbot)

## Features

- Conversational support for ads, copy, audiences, creatives, and scaling
- CSV/XLSX report upload and analysis
- Currency detection and minimum-spend checks before analysis
- Date-range validation when date columns are available
- Structured, decision-oriented responses (what to pause, scale, or fix)
- Follow-up interactions for report-based guidance
- Persistent user memory (last 20 messages + last report analysis)

## Requirements

- Python 3.9+ (3.12 recommended for production)

## Local Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create your environment file:

```bash
cp .env.example .env
```

3. Set required variables in `.env` (local development only):

- `TELEGRAM_BOT_TOKEN`
- `DEEPSEEK_API_KEY`

4. Run the bot:

```bash
python main.py
```

User data is stored in `./data/users.json` locally.

## Production Setup (Render)

Adley runs as a **background worker** on Render (not a web service — it uses Telegram long polling, not HTTP).

The repo includes a [`render.yaml`](render.yaml) Blueprint that configures everything automatically.

### Deploy with Blueprint

1. **Stop the Railway service first** — only one instance should poll the same bot token at a time.
2. Go to [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**.
3. Connect the GitHub repo: `Bamson-dev/Ad-Decision`.
4. Render will detect `render.yaml` and create the `ad-decision` worker.
5. When prompted, set these secret environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `DEEPSEEK_API_KEY`
6. Click **Apply** and wait for the first deploy to finish.
7. Check logs for `Adley is running...` and test the bot on Telegram.

### What the Blueprint configures

| Setting | Value |
|---------|-------|
| Service type | Background worker |
| Start command | `python main.py` |
| Build command | `pip install -r requirements.txt` |
| Python version | 3.12.8 |
| Persistent disk | 1 GB at `/opt/render/project/src/data` |
| Data path | `ADLEY_DATA_DIR=/opt/render/project/src/data` |

The persistent disk keeps `users.json` (conversation memory) across redeploys.

### Manual Render setup (without Blueprint)

If you prefer the dashboard:

1. **New** → **Background Worker** → connect the repo.
2. **Build command:** `pip install -r requirements.txt`
3. **Start command:** `python main.py`
4. **Environment variables:**
   - `TELEGRAM_BOT_TOKEN` (secret)
   - `DEEPSEEK_API_KEY` (secret)
   - `ADLEY_DATA_DIR` = `/opt/render/project/src/data`
   - `PYTHON_VERSION` = `3.12.8`
5. **Disks** → Add disk → mount path `/opt/render/project/src/data`, size 1 GB.
6. Deploy.

### Migrating user data from Railway

If you had a persistent volume on Railway at `/app/data`:

1. Download `users.json` from the Railway volume before shutting down.
2. After Render deploys, open a **Shell** on the worker (Render Dashboard → your service → Shell).
3. Copy the file into the mounted disk:
   ```bash
   # paste or upload users.json, then:
   cp /tmp/users.json /opt/render/project/src/data/users.json
   ```
4. Restart the worker.

### After migration

Once Render is confirmed working:

1. Delete or pause the Railway service to avoid duplicate billing.
2. Remove Railway environment variables if no longer needed.

## Commands

- `/start` - Intro and quick usage
- `/help` - Export steps for Meta Ads Manager reports
- `/reset` - Resets conversation history (keeps last report analysis)
