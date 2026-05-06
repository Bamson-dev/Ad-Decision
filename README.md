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

## Requirements

- Python 3.9+

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

## Production Setup (Railway)

Set these as service variables in Railway (instead of using a local `.env` file):

- `TELEGRAM_BOT_TOKEN`
- `DEEPSEEK_API_KEY`

## Commands

- `/start` - Intro and quick usage
- `/help` - Export steps for Meta Ads Manager reports
- `/reset` - Resets conversation history
