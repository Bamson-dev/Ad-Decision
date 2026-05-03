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

- `TELEGRAM_BOT_TOKEN`
- `DEEPSEEK_API_KEY`

4. Run the bot:

```bash
python main.py
```

## Usage

- Send `/start` to see a quick intro.
- Send `/help` to get step-by-step Meta export instructions.
- Send your ad report file as a Telegram document (`.csv` or `.xlsx`).
