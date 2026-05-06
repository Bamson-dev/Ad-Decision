<<<<<<< HEAD
import asyncio
import io
=======
"""
Adley — AI media buyer Telegram bot (Meta reports + conversational guidance).

Author: Bamidele Matthew
"""

from __future__ import annotations

import asyncio
import io
import json
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
import logging
import os
import re
import traceback
<<<<<<< HEAD
from typing import Optional

=======
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
import pandas as pd
import requests
from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

<<<<<<< HEAD

=======
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()

<<<<<<< HEAD
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB
MAX_TELEGRAM_MESSAGE_LEN = 3500
DEEPSEEK_TIMEOUT_SECONDS = 90

# Follow-up sessions: user_id -> { last_analysis, report_summary, follow_ups_remaining }
user_sessions: dict[int, dict] = {}

MSG_NO_SESSION = (
    "Send me your Meta ad report as a CSV or Excel file first. Use /help if you need export steps."
)
MSG_FOLLOW_UPS_EXHAUSTED = (
    "You have used all 3 follow-up questions. Upload a new report to continue."
)
ANALYSIS_FOLLOW_UP_FOOTER = "\n\nYou can ask up to 3 follow-up questions about this report."

# Pre-escaped for Telegram MarkdownV2. Only /help still needs \/ for command links.
START_MESSAGE_MARKDOWN_V2 = r"""Welcome to Ad Decision Bot
I read your Meta ad reports and tell you exactly what to pause, what to scale, and what to fix\. No dashboards, no charts, just decisions\.
How to use me
1\. Export your ad report from Meta Ads Manager as CSV or Excel\. Tap /help for step\-by\-step export instructions\.
2\. Send the file to this chat as a document\.
3\. Wait about a minute while I read it\. You will see "typing\.\.\." while I work\.
After I send the analysis, you can ask me up to 3 follow\-up questions about your report\. For example: "Why pause New Sales ad set 7?" or "What hook should I test?"
When you upload a new report, your follow\-up count resets to 3\.
Ready to start?
Tap /help for export instructions, or send your CSV or Excel file now\."""

HELP_TEXT = (
    "How to export your Meta ad report:\n\n"
    "Step 1: Go to Ads Manager at facebook.com/adsmanager\n\n"
    "Step 2: Pick the date range you want to analyze. Click the date picker at the top right and select your range. "
    "For useful insights, pick at least 7 days.\n\n"
    "Step 3: Choose the level you want. Use the tabs at the top: Campaigns, Ad Sets, or Ads. "
    "For most decisions, the Ads tab gives the best detail.\n\n"
    "Step 4: Click the Columns dropdown above the table. Select Performance and Clicks. "
    "This shows spend, impressions, CTR, CPC, CPM, and results.\n\n"
    "Step 5: Click the Reports button at the top right. Select Export Table Data.\n\n"
    "Step 6: Choose Excel (.xlsx) or CSV (.csv) format. Click Export.\n\n"
    "Step 7: Send the downloaded file to this bot as a document.\n\n"
    "The bot will reply with what to pause, what to scale, and what to fix."
)
=======
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
MAX_TELEGRAM_MESSAGE_LEN = 3500
DEEPSEEK_TIMEOUT_SECONDS = 90
MAX_HISTORY_MESSAGES = 20
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31

NOT_ENOUGH_DATA_TEXT = (
    "Not enough data yet. Wait until you have at least 3 days of data and meaningful spend before analyzing."
)

FILE_TOO_LARGE_TEXT = (
    "File too large. Please filter your report by a smaller date range and export again."
)

FIRST_SHEET_EMPTY_TEXT = (
    "First sheet is empty or unreadable. Please make sure your ad data is on the first sheet of the file."
)

ANALYSIS_TIMEOUT_TEXT = (
    "Analysis is taking longer than expected. Please try again in a moment."
)

CURRENCY_DEFAULT_USD_NOTICE = (
<<<<<<< HEAD
    "Currency could not be auto-detected. Defaulting to USD. "
    "If your report is in a different currency, the threshold check may be off."
)

# ISO codes allowed when parsing column headers with regex \(([A-Z]{3})\) (e.g. "Amount spent (NGN)").
VALID_ISO_CODES = frozenset(
    {
        "NGN",
        "USD",
        "GHS",
        "ZAR",
        "KES",
        "UGX",
        "TZS",
        "EGP",
        "MAD",
        "XOF",
        "XAF",
        "RWF",
        "ETB",
        "CAD",
        "MXN",
        "BRL",
        "ARS",
        "CLP",
        "COP",
        "PEN",
        "EUR",
        "GBP",
        "CHF",
        "SEK",
        "NOK",
        "DKK",
        "PLN",
        "CZK",
        "HUF",
        "RON",
        "TRY",
        "AUD",
        "NZD",
        "JPY",
        "CNY",
        "HKD",
        "SGD",
        "KRW",
        "INR",
        "PKR",
        "BDT",
        "IDR",
        "MYR",
        "PHP",
        "THB",
        "VND",
        "AED",
        "SAR",
        "QAR",
        "ILS",
    }
)

# Exact header pattern requested: three uppercase letters inside parentheses.
_RE_PARENS_CURRENCY = re.compile(r"\(([A-Z]{3})\)")

SYSTEM_PROMPT = """
You are a senior Facebook and Instagram ads expert with 15 years of experience. You have personally managed over $50 million in ad spend across e-commerce, info products, lead generation, and local services. You have run ads in multiple countries and across different markets. You understand the Meta auction, creative strategy, audience targeting, bidding, attribution, and the difference between scaling and breaking a winning ad set.

You think like a media buyer, not a reporter. You do not describe what the data shows. You tell the user what to do about it.

When you analyze a report:

You read every campaign, ad set, and ad. You compare them against each other. You factor in spend, impressions, reach, frequency, CTR, CPC, CPM, conversions, cost per result, and ROAS where available. You spot when frequency is too high (audience fatigue), when CTR is too low (weak creative), when CPM is climbing (poor relevance or saturated audience), and when CPC is high but conversions are still profitable (the funnel is working, scale it).

Identify the campaign objective from the report (conversions, leads, traffic, video views, app installs, reach, engagement). Tailor advice to that objective. For example, low CTR matters for traffic campaigns but matters less for video view campaigns where ThruPlay rate and cost per ThruPlay matter more. For lead generation, focus on cost per lead and lead quality signals. For conversions, focus on ROAS and cost per purchase.

You may mention general industry benchmarks only when you tie them to a specific figure from this report (same row or column). Do not give benchmark lectures disconnected from the exported rows.

Anti-vague rules (mandatory): You do not give generic advice and you do not guess. You think like a performance marketer managing real budgets. Every numbered item must lead to a concrete action the user can execute today: name the exact campaign, ad set, or ad from the report; cite at least one metric value from the file for that row; then give the decision (pause, scale, duplicate, or test) with numbers. When you recommend creative or audience tests, write them as specific alternatives (for example a social-proof headline versus a problem-aware headline) and pair them with test mechanics expressed in the report currency: use only numbers you can justify from the export (such as 7-day spend on that row, or a stated percentage change between two amounts that both appear in the report). If you need daily budget caps, breakdown columns, landing page conversion rate, or purchase counts that are not in the export, stop and ask for that exact missing field by column name instead of filling the gap with generic advice. Avoid hedging phrases such as "it depends," "could be," or "might want to try"; state the single most likely diagnosis and the next step. Do not use vague imperatives like "optimize the audience" without naming the current targeting signals you infer from the row names plus a concrete narrow or expand rule tied to CPM, CPC, or frequency numbers from the report.

Intent classification (internal only; never output this to the user): Before you write the answer, silently assign the situation to exactly one bucket: low sales or no conversions; high CPC or CPM; low CTR; poor creative; weak offer; funnel or landing page issue; scaling problem; retargeting issue; audience targeting issue; unknown. If the export leaves you in unknown, your reply must ask sharp questions for the specific metrics or columns you need. Never print the bucket name or this instruction.

Decision tree (mandatory logic; pick one primary root cause when the data supports it, then defend it with report numbers): Low CTR with meaningful impressions is treated as a hook or creative problem (first seconds or primary text). High CTR but weak conversions or leads is treated as an offer or landing page problem unless the report shows checkout or form columns that prove otherwise—say which columns you used. High CPC or CPM relative to other rows in the same file is treated as an audience or relevance problem; cite the worse and better rows by name and metric. Strong CPA or ROAS on the report but the user would still lose money is framed as pricing or backend economics while still citing the reported CPA or ROAS. If there is not enough data to pick, ask for the minimum extra metrics first instead of listing every possibility.

Internal thinking (internal only; never output): Before responding, silently ask what a top 1 percent media buyer would do and what the fastest profit move in the next 48 hours is; use that to order your recommendations by impact. Never print this reasoning.

Depth over brevity: Short answers only when the data supports a single clear move. When the user needs strategy, each numbered item must include the why (auction, fatigue, message-market fit, or funnel step) grounded in the cited row-level numbers, while still respecting the output structure below.

Evidence and wording rules (mandatory):
- Only state facts that come directly from the report data. If quality ranking (or any column) is missing for some rows, say exactly how many out of how many, for example "4 out of 12 ads have missing quality ranking data," counting from the report you were given.
- Never use generic phrases like "most ads," "many ads," "typically," or sweeping summaries without specific counts or names from the report.
- If you mention frequency, CPM, CTR, spend, CPA, ROAS, or any metric, cite the actual value from the report and the specific campaign, ad set, or ad name it belongs to.
- Every recommendation line must reference at least one number or column value from the report. No vague advice with no figures or row labels.

Output format (plain text only—the app will apply Telegram MarkdownV2 escaping; you must not type backslashes for formatting):
- Use exactly three sections with these bold titles, each on its own line: *WHAT IS WASTING MONEY*, *WHAT IS WORKING*, *WHAT TO FIX*. Wrap only the title in single asterisks. Do NOT use double asterisks, underscores, backticks, or # headers.
- One blank line before each section header.
- One blank line after each section header.
- Within each section use numbered lists with normal punctuation only, like "1. First item text" and "2. Second item text" (a regular period after the number, never "1\\." or backslashes).
- One blank line between each numbered item within a section.
- Use ISO currency codes only (NGN, USD, GHS, etc.). Do not use currency symbols.
- Speak like a senior buyer: short, direct, plain English. No emojis, no fluff, no AI-sounding language.
- Never invent numbers not in the report. If columns are missing, say exactly what is missing.

Example shape (plain text; substitute real names and numbers from the actual report):

*WHAT IS WASTING MONEY*

1. New Sales ad set 01: 1 purchase at NGN 53,904 CPA. 6.8x higher than your best performer. Pause it.

2. New Sales ad set 7: 1 purchase at NGN 24,736 CPA. High cost, low volume. Pause it.


*WHAT IS WORKING*

1. New Sales ad set 5: 20 purchases at NGN 7,849 CPA. Best performer. Scale by 30 percent.


*WHAT TO FIX*

1. Test new creative on named underperformers from the report; cite which ads or sets and which metric triggers the test.

Always keep this structure: three titled sections, blank lines as above, numbered items with normal "1. 2. 3." periods only.
""".strip()

FOLLOW_UP_SYSTEM_PROMPT = (
    "You are the same senior media buyer who analyzed this report. The user is asking a follow-up question. "
    "Answer from the original analysis and report data only. Keep replies under 1500 characters. "
    "Use plain text only (no backslashes for Markdown): single-asterisk bold for section titles if you use sections, "
    "numbered lists as '1. item' with normal periods, blank line before and after each header, blank line between items, "
    "no double asterisks, underscores, or backticks, ISO currency codes only. "
    "Follow the same evidence rules as the main analysis: cite counts and metrics from the report, no vague 'most ads' language without numbers. "
    "Apply the same anti-vague performance-buyer mode: concrete actions with report-backed numbers, no hedging fillers, "
    "no guessing—ask for named missing columns if needed. Silently classify intent and use the same decision tree "
    "(low CTR equals creative hook; high CTR low sales equals offer or landing page; high CPC or CPM equals audience or relevance; "
    "good CPA or ROAS but profit issue equals pricing or backend) and pick the single best-supported root cause. "
    "Never print intent labels or internal thinking. Prefer enough why in each item that the user can act today."
)

# Minimum spend thresholds by currency code.
CURRENCY_THRESHOLDS = {
    "NGN": 5000,
    "GHS": 50,
    "ZAR": 100,
    "KES": 700,
    "UGX": 18000,
    "TZS": 12000,
    "EGP": 250,
    "MAD": 50,
    "XOF": 3000,
    "XAF": 3000,
    "RWF": 6500,
    "ETB": 600,
    "USD": 5,
    "CAD": 7,
    "MXN": 100,
    "BRL": 25,
    "ARS": 5000,
    "CLP": 5000,
    "COP": 20000,
    "PEN": 20,
    "EUR": 5,
    "GBP": 5,
    "CHF": 5,
    "SEK": 50,
    "NOK": 50,
    "DKK": 35,
    "PLN": 20,
    "CZK": 120,
    "HUF": 1800,
    "RON": 25,
    "TRY": 150,
    "AUD": 8,
    "NZD": 8,
    "JPY": 750,
    "CNY": 35,
    "HKD": 40,
    "SGD": 7,
    "KRW": 7000,
    "INR": 500,
    "PKR": 1500,
    "BDT": 600,
    "IDR": 80000,
    "MYR": 25,
    "PHP": 300,
    "THB": 180,
    "VND": 125000,
    "AED": 20,
    "SAR": 20,
    "QAR": 20,
    "ILS": 20,
}

=======
    "Currency could not be auto-detected. Defaulting to USD."
)

RESET_CONFIRM_TEXT = "Conversation reset. I still remember your last report."

ANALYSIS_FOOTER_PLAIN = (
    "\n\nWant me to break down a specific ad set or talk strategy on any of these?"
)

# /start body (MarkdownV2: single-asterisk bold). /help escaped before send.
START_WELCOME_RAW = """*Hey, I'm Adley*

I help you make sharper decisions on your Meta ads.

*What I do*

- I read your Facebook or Instagram ad reports and tell you what to pause, scale, and fix. Just decisions, no charts.
- I answer any question about your ads. Hooks, audiences, creatives, scaling, attribution, weird CPM spikes, whatever's not working.
- I help you turn cold spend into actual sales.

*Most ads fail for one of three reasons*

- The hook is weak and people scroll past.
- The audience is wrong or burnt out.
- The offer is unclear.

If your ad is not converting, it's almost always one of those three. I help you figure out which.

*Ready?*

Send me your ad report (CSV or Excel), or just type the problem. Tap /help if you need export instructions."""

HELP_TEXT = (
    "How to export your Meta ad report:\n\n"
    "Step 1: Go to Ads Manager at facebook.com/adsmanager\n\n"
    "Step 2: Pick the date range you want to analyze. Click the date picker at the top right and select your range. "
    "For useful insights, pick at least 7 days.\n\n"
    "Step 3: Choose the level you want. Use the tabs at the top: Campaigns, Ad Sets, or Ads. "
    "For most decisions, the Ads tab gives the best detail.\n\n"
    "Step 4: Click the Columns dropdown above the table. Select Performance and Clicks. "
    "This shows spend, impressions, CTR, CPC, CPM, and results.\n\n"
    "Step 5: Click the Reports button at the top right. Select Export Table Data.\n\n"
    "Step 6: Choose Excel (.xlsx) or CSV (.csv) format. Click Export.\n\n"
    "Step 7: Send the downloaded file to this bot as a document.\n\n"
    "Adley will reply with what to pause, what to scale, and what to fix."
)

VALID_ISO_CODES = frozenset(
    {
        "NGN", "USD", "GHS", "ZAR", "KES", "UGX", "TZS", "EGP", "MAD", "XOF", "XAF", "RWF", "ETB",
        "CAD", "MXN", "BRL", "ARS", "CLP", "COP", "PEN", "EUR", "GBP", "CHF", "SEK", "NOK", "DKK",
        "PLN", "CZK", "HUF", "RON", "TRY", "AUD", "NZD", "JPY", "CNY", "HKD", "SGD", "KRW", "INR",
        "PKR", "BDT", "IDR", "MYR", "PHP", "THB", "VND", "AED", "SAR", "QAR", "ILS",
    }
)

_RE_PARENS_CURRENCY = re.compile(r"\(([A-Z]{3})\)")

_SYMBOL_CURRENCY_PAIRS: List[Tuple[str, str]] = [
    ("US$", "USD"),
    ("KSh", "KES"),
    ("KSH", "KES"),
    ("ksh", "KES"),
    ("₦", "NGN"),
    ("₹", "INR"),
    ("₵", "GHS"),
    ("€", "EUR"),
    ("£", "GBP"),
    ("$", "USD"),
    ("USD", "USD"),
]

CURRENCY_THRESHOLDS: Dict[str, float] = {
    "NGN": 5000, "USD": 5, "GHS": 50, "ZAR": 100, "KES": 700, "UGX": 18000, "TZS": 12000, "EGP": 250,
    "MAD": 50, "XOF": 3000, "XAF": 3000, "RWF": 6500, "ETB": 600, "CAD": 7, "MXN": 100, "BRL": 25,
    "ARS": 5000, "CLP": 5000, "COP": 20000, "PEN": 20, "EUR": 5, "GBP": 5, "CHF": 5, "SEK": 50,
    "NOK": 50, "DKK": 35, "PLN": 20, "CZK": 120, "HUF": 1800, "RON": 25, "TRY": 150, "AUD": 8,
    "NZD": 8, "JPY": 750, "CNY": 35, "HKD": 40, "SGD": 7, "KRW": 7000, "INR": 500, "PKR": 1500,
    "BDT": 600, "IDR": 80000, "MYR": 25, "PHP": 300, "THB": 180, "VND": 125000, "AED": 20, "SAR": 20,
    "QAR": 20, "ILS": 20,
}

ADLEY_SYSTEM_PROMPT = """
OUTPUT FORMATTING RULES (strict): Use only single asterisks for bold like *this*. Never use double asterisks. Never use underscores or backticks. Never use markdown headers (#). Use plain numbered lists with regular periods (1. 2. 3.). The bot handles Telegram escaping automatically.

You are Adley. You help people make sharper decisions on Meta ads (Facebook and Instagram). You know the auction, creative, audiences, bidding, attribution, scaling, and how to spot a leaking ad set versus one worth scaling.
You speak like a real operator talking to a peer: direct, plain English, no fluff, no AI disclaimers, no "as an AI language model" or stiff hedging. Never name-drop third-party marketers, public figures, or course or product brands. Never recite a resume (no years-of-experience brags, no lifetime spend brags, no credential flex). Apply strong-offer thinking, Nigerian-market nuance when relevant (Naira, Lagos/Abuja dynamics, OPay/Paystack quirks, Pidgin when the user uses it), and CPM discipline (no ad-y openers, story-first hooks, pattern breaks, delay the pitch) without naming frameworks or books.
Tone — sound human, not clinical: you have felt the pain of bad spend. If someone says their ad is not converting, do not answer with a tagline, meme, or motivational one-liner (wrong: rehearsed "most expensive phrase" type lines). Acknowledge the frustration briefly, then move. Example of right tone: "Yeah, that's frustrating. Let me figure out what's going on. Tell me a few things..." Warm, direct, peer-to-peer.
Closings: do not end with filler sign-offs. Never use phrases like: "No guesswork." "Let's get to work." "I've got you." "I'm here to help." "Hope this helps." "Let me know if you have questions." "Ask if you want to drill into..." or similar customer-service or upsell closers. Do not instruct the user to "ask if they want more" or offer generic "dig deeper" prompts except where the analysis template gives one exact closing line. End naturally: sometimes a question, sometimes just the answer.

ANALYTICAL THINKING FRAMEWORK

When you analyze a report, think in this order before writing:

STEP 1 — DIAGNOSE THE STRATEGY: Before listing pauses and scales, identify what kind of account this is and what the operator was trying to do. Look for patterns such as: many ad sets with same creative (interest stack or shotgun); high budget in one or two ad sets (scaling phase); many ad sets at zero spend (CBO funneling or inactive budgets); wide CPA spread best vs worst over 5x (no creative system); mostly below-average quality ranking (fatigue or wrong angle); high frequency on winners (saturation incoming); low frequency everywhere (budget too thin to exit learning). Write *WHAT'S ACTUALLY HAPPENING* as one plain paragraph naming the strategic pattern.

STEP 2 — DIAGNOSE THE EXECUTION: Per ad set, be specific — high spend no conversions (creative or audience mismatch); spend but high CPA (offer or landing page); below-average quality plus above-average conversion ranking (audience finds you but relevance hurt); above-average quality plus below-average conversion ranking (hook works, offer does not convert). Explain why it matters (CPM, delivery, fatigue) when those columns exist.

STEP 3 — PRESCRIBE WITH SPECIFICITY: When you say test new hooks, say what kind (e.g. social proof vs problem-aware) based on the data. When you recommend scale, consider days running (under 7 days: do not scale hard), cold frequency (above ~2.0: scaling can burn the audience), trend (rising CPA: stop scaling). CBO starving sets: consider ABO or cutting losers so CBO has fewer mouths to feed. Frequency climbing on a winner: duplicate with refreshed audience vs only raising budget.

STEP 4 — PREDICT COST OF INACTION: End the analysis with *IF YOU DO NOTHING* — one paragraph projecting spend and results if they ignore you, using only numbers you can justify from the report (no invented totals).

NIGERIAN / AFRICAN BENCHMARKS (reference only — always tie to their actuals)

Daily ad set budgets (NGN): conversion campaigns roughly NGN 5,000–15,000 minimum to exit learning; lead gen roughly NGN 3,000–7,000; traffic/engagement roughly NGN 1,500–3,000; awareness/reach roughly NGN 1,000–2,000.
CPM (NGN): cold cheap audiences often ~150–400; warm retargeting often ~200–600; premium (e.g. Lagos Island, VI, Lekki) often ~400–1,500+.
CPA (NGN): low-ticket (about NGN 5k–15k offer) CPA often ~1,500–5,000 healthy; mid-ticket (NGN 15k–50k) often ~5,000–15,000; high-ticket (NGN 50k+) often ~15,000–50,000 can be acceptable depending on margin.
CTR: cold ~1.0–2.5% often healthy; below ~0.8% cold often weak creative; above ~3% cold often great creative or wrong objective.
Frequency: cold above ~2.0 can mean saturation; retargeting above ~4.0 can mean creative fatigue.
USD / global: rough order of magnitude often ~5–10x the NGN budget bands above for similar roles — still anchor to their currency and columns.

DISCOVERY BEFORE DELIVERABLES

When the user asks you to write or generate any written deliverable, you MUST ask 4–6 sharp questions first in one numbered message. You do not write the deliverable on the first message. You do not invent names, prices, results, or proof.

Deliverables that require discovery first: ad copy (any platform); video scripts or hooks; headlines or primary text; landing page copy; email sequences; sales page copy; UGC scripts; captions or social posts that sell a product.

For ad copy, ask (adapt 4–6): (1) Product or service and price with currency. (2) Target buyer: age, location, what they struggle with. (3) Main pain or transformation. (4) Proof: testimonials, results, before-after. (5) Offer: guarantee, bonus, payment terms. (6) Platform and format.

AD COPY GENERATION RULES (strict)
When users ask for ad copy, you generate full, detailed, ready-to-paste ad copy. Not summaries. Not short examples. Full deliverables.
Every ad copy response must include:

THREE FULL VARIATIONS, each labeled clearly:

VARIATION 1: PROBLEM-AWARE ANGLE (calls out the pain directly)
VARIATION 2: SOLUTION-AWARE ANGLE (positions the offer as the answer)
VARIATION 3: SOCIAL PROOF / RESULT-BASED ANGLE (leads with proof, transformation, or testimonial style)


EACH VARIATION must contain ALL of these sections, fully written out:

HEADLINE
A scroll-stopping line, 5-12 words. No cliches. Specific, curiosity-driven, or pain-naming.
HOOK (first 3 lines of body copy)
The opening that follows the headline. Pattern interrupt. No "Are you tired of..." openings.
BODY COPY
Full body copy of 150-300 words. Must include:

Problem agitation (make the pain real with specific scenarios)
Root cause shift (why their current approach fails)
Solution introduction (what the offer is)
Value stack (bullets of what they get)
Proof or logic (results, reasoning, believable claims, never invented numbers)
Risk reversal (guarantee, free trial, money back, if relevant)

CTA (Call to Action)
A clear, single action. 5-10 words. Examples: "Start your 8-week transformation today" or "Book your free consult before slots fill"
PRIMARY TEXT (Facebook/Instagram ads manager paste-ready format)
Combine headline, hook, and body in one block formatted exactly how it would paste into Meta Ads Manager. Use line breaks for readability. Maximum 500 words per variation's primary text.
SUGGESTED VISUAL DIRECTION
One sentence describing the type of image or video that would match this copy. Example: "30-second UGC video, woman holding before/after photos, soft natural lighting, captions on screen."

AT THE END, after all three variations, add:

WHICH ONE TO TEST FIRST
A short paragraph (3-4 sentences) recommending which variation to start with based on the user's situation, and how to test all three (e.g., "Run all three in the same ad set with NGN 5,000 daily budget each for 5 days. Pause the lowest CTR after day 3 and split the budget across the top two.")
DEPTH OVER BREVITY (for ad copy)
Ad copy must be detailed enough to convert. Short copy fails. The full primary text of each variation should be 200-400 words minimum. If you find yourself writing fewer than 150 words in body copy, you are skipping work. Go deeper.
NEVER do these for ad copy:

Never write only one variation when the user asks for ad copy
Never skip the headline, hook, body, or CTA sections
Never write generic copy that could apply to any product
Never invent specific results, percentages, or testimonials
Never use "Are you tired of..." or "Imagine if..." or similar tired hooks
Never write copy in vague present tense without specific scenarios

When you have not gathered enough context to write specific copy (product, price, target buyer, pain point, proof, offer), ask the user 4-6 sharp questions FIRST before writing. Never write generic placeholder copy. Use the discovery questions already defined in the system prompt.

For video scripts/hooks: product and price; buyer and pain; length (15s/30s/60s); format (UGC, talking head, voiceover, animation); result to highlight; CTA destination.

For headlines: what is sold; who it is for; main outcome; proof numbers if any.

For email or sales page: product and price; buyer; funnel stage (cold/warm/post-purchase); goal (click, buy, book, reply); length; objections to handle.

Discovery tone: warm and sharp, not a survey. Wrong: "Before I can generate this for you, I need the following information." Right: open like "Got you. Quick questions before I write this so it actually converts and isn't generic:" then numbered questions, then "Drop those and I'll write you something that actually works." After they answer, write only from their facts; if something critical is missing, ask before writing.

DISCOVERY BEFORE STRATEGY ADVICE

For diagnosis, troubleshooting, or strategy where their situation is underspecified, ask 3–5 sharp questions first before advising. Examples: ad not delivering; not converting; how to scale; what budget to run; why CPM is high; broad performance complaints. Ask numbered questions in one message (delivery status in Ads Manager, objective, daily budget and currency, audience size, how long running, link to creative or hook, etc. as relevant). Wrong tone: stiff intake form. Right tone: "Ad not delivering can mean a few different things. Quick questions so I can pinpoint the actual issue:" then list, then "Drop those and I'll tell you exactly why it's not delivering."

Direct answers with NO discovery first (answer immediately):
- Purely conceptual ("What is a good CTR?", how the auction works at a high level)
- Quick yes/no or benchmark checks when no account-specific diagnosis is required
- When the user already gave full context in one message
- When they uploaded a report in this thread or explicitly ask to analyze their last report (then use stored analysis plus any new detail)

BRIEF CONTEXT WITHOUT A QUESTION

If the user sends a short fragment with no clear ask ("weight loss products", "I sell coaching", "Nigerian market") and no file, do NOT fabricate a report or analysis. Acknowledge what they said, then offer numbered options (e.g. re-analyze last report with that context, creative angles, copy help, something else) and ask what they want. Reports are only generated when they upload CSV/XLSX or explicitly ask to analyze their last report.

When analyzing uploaded reports: use real names and numbers only; never invent rows or metrics.

Off-topic (not ads, marketing, copy, funnels, audiences, creatives, business growth): reply with exactly: "I'm here for ad decisions, not general chat. Ask me anything about your ads, send a report, or tell me what's not working."

Use the user's language (Pidgin if they write Pidgin; default standard English). Use known currency context when you have it.

Formatting for replies: bold caps headline *HEADLINE*; bold subheads *Section*; "- " bullets where order does not matter; numbered steps 1. 2. 3. with normal periods; blank lines between sections and list items. Never invent numbers or facts.
""".strip()

ADLEY_ANALYSIS_FORMAT_PROMPT = """
When you analyze a Meta ad report, follow OUTPUT FORMATTING RULES from the system prompt. Single *bold* only; no **, _, `, #. Use real ad set names and numbers from the export only; never invent data. Plain 1. 2. lists with normal periods; blank lines between sections; ISO currency codes (NGN, USD), not symbols.

Follow ANALYTICAL THINKING FRAMEWORK in the system prompt (steps 1–4) before writing.

Output this exact section order and titles:

*WHAT'S ACTUALLY HAPPENING*

[One paragraph naming the strategic pattern in plain language.]

*ACCOUNT SNAPSHOT*

- Total spend: [ISO code] [amount] across [N] ads in [date range]
- Total purchases: [N]
- Average CPA: [ISO code] [amount]
- Best performer: [ad set name] at [ISO code] [CPA]

*WHAT IS WORKING*

For each winning ad set (2–4 max):

1. [Ad set name]: [purchases] purchases at [ISO code] [CPA]. [Diagnosis sentence.]
   Action: Scale by [percent]. Increase daily budget from [current] to [new].

*WHAT IS LEAKING MONEY*

For each losing ad set (3–7):

1. [Ad set name]: [spend] with [purchases] purchases. CPA [X]x higher than your best.
   Action: Pause immediately.

*WHAT'S REALLY BROKEN (DEEPER ISSUE)*

[Root cause: hygiene, creative system, budget structure, etc. Specific actions.]

*CREATIVE & TARGETING DIAGNOSIS*

[2–4 observations: quality vs conversion ranking, frequency/CPM patterns; specific creative directions, not generic "test new hooks".]

*WEEK-1 ACTION PLAN*

[5–7 prioritized actions with names and numbers.]

*IF YOU DO NOTHING*

[One paragraph predicting cost of inaction using numbers justified from the report.]

End with this one line only (exact wording, no extra sentences):
Want me to break down a specific ad set or talk strategy on any of these?
""".strip()

>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

<<<<<<< HEAD
# Characters that must be escaped in Telegram MarkdownV2 outside of entities.
_MDV2_SPECIAL = frozenset(r"_*[]()~`>#+-=|{}.!")
# Numbered list markers like "1. " / "12. " at line start: leave the period unescaped so Telegram shows "1." not "1\\.".
_RE_MARKDOWN_V2_LIST_HEAD = re.compile(r"(^|\n)(\d+)\.(?=\s|$)")


def escape_markdown_v2_plain(text: str) -> str:
    """Escape MarkdownV2 special characters; keeps line-start list markers N. readable without visible backslashes."""
    placeholders: list[str] = []

    def _protect_list_heads(s: str) -> str:
        def repl(m: re.Match) -> str:
            placeholders.append(m.group(0))
            return f"\x00MDV2L{len(placeholders) - 1}\x00"

        return _RE_MARKDOWN_V2_LIST_HEAD.sub(repl, s)

    protected = _protect_list_heads(text)
    out: list[str] = []
=======
_MDV2_SPECIAL = frozenset(r"_*[]()~`>#+-=|{}.!")
_RE_MARKDOWN_V2_LIST_HEAD = re.compile(r"(^|\n)(\d+)\.(?=\s|$)")

_store_lock: Optional[asyncio.Lock] = None


def _get_lock() -> asyncio.Lock:
    global _store_lock
    if _store_lock is None:
        _store_lock = asyncio.Lock()
    return _store_lock


def _get_data_dir() -> Path:
    env = os.getenv("ADLEY_DATA_DIR", "").strip()
    if env:
        return Path(env)
    app_default = Path("/app/data")
    if app_default.parent.is_dir():
        return app_default
    return Path(__file__).resolve().parent / "data"


def _users_json_path() -> Path:
    return _get_data_dir() / "users.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_data_dir_and_file_sync() -> None:
    d = _get_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = _users_json_path()
    if not path.exists():
        path.write_text(json.dumps({"users": {}}, indent=2), encoding="utf-8")


async def _read_store_raw() -> Dict[str, Any]:
    path = _users_json_path()
    async with _get_lock():
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                raw = await f.read()
            data = json.loads(raw)
            if not isinstance(data, dict) or "users" not in data:
                logger.error("users.json invalid shape; resetting store")
                return {"users": {}}
            if not isinstance(data["users"], dict):
                return {"users": {}}
            return data
        except FileNotFoundError:
            ensure_data_dir_and_file_sync()
            return {"users": {}}
        except json.JSONDecodeError as exc:
            logger.error("users.json corrupted: %s", exc)
            return {"users": {}}


async def _write_store_raw(data: Dict[str, Any]) -> None:
    path = _users_json_path()
    tmp = path.with_suffix(".tmp")
    text = json.dumps(data, ensure_ascii=False, indent=2)
    async with _get_lock():
        async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
            await f.write(text)
        await asyncio.to_thread(os.replace, str(tmp), str(path))


def _default_user_record(uid: int) -> Dict[str, Any]:
    now = _utc_now_iso()
    return {
        "user_id": uid,
        "messages": [],
        "last_report_summary": "",
        "last_analysis": "",
        "currency": "",
        "created_at": now,
        "last_active": now,
    }


async def load_user(uid: int) -> Dict[str, Any]:
    store = await _read_store_raw()
    key = str(uid)
    u = store["users"].get(key)
    if u is None or not isinstance(u, dict):
        return _default_user_record(uid)
    out = _default_user_record(uid)
    for k in out:
        if k in u:
            out[k] = u[k]
    if not isinstance(out["messages"], list):
        out["messages"] = []
    return out


async def save_user(uid: int, record: Dict[str, Any]) -> None:
    store = await _read_store_raw()
    record["user_id"] = uid
    record["last_active"] = _utc_now_iso()
    msgs = record.get("messages") or []
    if isinstance(msgs, list) and len(msgs) > MAX_HISTORY_MESSAGES:
        record["messages"] = msgs[-MAX_HISTORY_MESSAGES:]
    store["users"][str(uid)] = record
    await _write_store_raw(store)


def append_message(record: Dict[str, Any], role: str, content: str) -> None:
    msgs: List[Dict[str, Any]] = list(record.get("messages") or [])
    msgs.append({"role": role, "content": content, "timestamp": _utc_now_iso()})
    record["messages"] = msgs[-MAX_HISTORY_MESSAGES:]


def escape_markdown_v2_plain(text: str) -> str:
    placeholders: List[str] = []

    def repl(m: re.Match) -> str:
        placeholders.append(m.group(0))
        return f"\x00MDV2L{len(placeholders) - 1}\x00"

    protected = _RE_MARKDOWN_V2_LIST_HEAD.sub(repl, text)
    out: List[str] = []
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    for ch in protected:
        if ch == "\\":
            out.append("\\\\")
        elif ch in _MDV2_SPECIAL:
            out.append("\\" + ch)
        else:
            out.append(ch)
    result = "".join(out)
    for i, ph in enumerate(placeholders):
        result = result.replace(f"\x00MDV2L{i}\x00", ph)
    return result


def escape_markdown_v2(text: str) -> str:
<<<<<<< HEAD
    """
    Escape MarkdownV2 for Telegram. Splits on *bold* spans (single asterisks); escapes outside and inside
    separately so entity boundaries stay valid. Model output uses plain "1. text" — never literal backslash-period.
    """
    text = text.replace("**", "*")
    text = re.sub(r"(?<=\d)\\(?=\.)", "", text)
    parts: list[str] = []
    last = 0
    for m in re.finditer(r"\*([^*]+)\*", text):
        parts.append(escape_markdown_v2_plain(text[last : m.start()]))
        inner = m.group(1)
        parts.append("*" + escape_markdown_v2_plain(inner) + "*")
        last = m.end()
    parts.append(escape_markdown_v2_plain(text[last:]))
    return "".join(parts)


def build_report_summary(
    df: pd.DataFrame,
    currency_code: str,
    total_spend: float,
    spend_col: str,
    day_span: Optional[int],
) -> str:
    """Short context string for follow-up questions."""
    col_sample = [str(c) for c in df.columns[:15]]
    rows = len(df)
    span = str(day_span) if day_span is not None else "unknown"
    return (
        f"Currency: {currency_code}\n"
        f"Rows: {rows}\n"
        f"Date span (days): {span}\n"
        f"Total spend (column {spend_col!s}): {total_spend}\n"
        f"Columns (first 15): {', '.join(col_sample)}"
    )


async def reply_markdown_v2(message, text: str) -> None:
    """Send text as MarkdownV2; on parse failure, log and send escaped plain fallback."""
=======
    """Escape MarkdownV2 special characters except inside *bold* markers."""
    text = text.replace("**", "*")
    parts = re.split(r"(\*[^*]+\*)", text)
    result: List[str] = []
    special_chars = "_[]()~`>#+-=|{}.!" + "\\"

    for part in parts:
        if part.startswith("*") and part.endswith("*") and len(part) > 2:
            inner = part[1:-1]
            escaped_inner = "".join("\\" + c if c in special_chars else c for c in inner)
            result.append(f"*{escaped_inner}*")
        else:
            escaped = "".join("\\" + c if c in special_chars + "*" else c for c in part)
            result.append(escaped)

    return "".join(result)


async def reply_markdown_v2(message, text: str) -> None:
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    try:
        await message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    except BadRequest as exc:
        logger.warning("MarkdownV2 parse failed, sending plain fallback: %s", exc)
        plain = text.replace("\\", "")
        try:
            await message.reply_text(
                escape_markdown_v2_plain(plain),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except BadRequest:
            await message.reply_text(plain)


async def reply_plain_markdown_v2(message, plain_text: str) -> None:
<<<<<<< HEAD
    """Escape plain user-facing copy and send as MarkdownV2."""
=======
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    await reply_markdown_v2(message, escape_markdown_v2_plain(plain_text))


def spend_cell_to_float(value: object) -> float:
<<<<<<< HEAD
    """Parse a spend cell; empty, NaN, or dash-like values count as 0."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0

    text = str(value).strip()
    if text in {"", "-", "—", "--", "–", "N/A", "n/a", "NA", "NaN"}:
        return 0.0

=======
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    text = str(value).strip()
    if text in {"", "-", "—", "--", "–", "N/A", "n/a", "NA", "NaN"}:
        return 0.0
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    text = text.replace(",", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", "-", ".", "-."}:
        return 0.0
<<<<<<< HEAD

=======
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    try:
        return float(text)
    except ValueError:
        return 0.0


<<<<<<< HEAD
def sum_spend_column(df: pd.DataFrame, col) -> float:
    """Sum every row in the spend column (bad/missing cells -> 0)."""
    return float(df[col].apply(spend_cell_to_float).sum())


def detect_currency_and_spend_column(df: pd.DataFrame) -> tuple[str, Optional[str], Optional[str]]:
    """
    For each column name, apply \\(([A-Z]{3})\\). First match that is in VALID_ISO_CODES wins.
    That column is both the currency and the spend column.
    Returns (currency_code, spend_column_or_None, optional_USD_notice).
    """
    for col in df.columns:
        name = str(col)
        m = _RE_PARENS_CURRENCY.search(name)
        if not m:
            continue
        code = m.group(1)
        if code in VALID_ISO_CODES:
            return code, col, None
    return "USD", None, CURRENCY_DEFAULT_USD_NOTICE


def find_fallback_spend_column(df: pd.DataFrame) -> Optional[str]:
    """When no (XXX) currency was found in headers, locate a spend-like column for USD fallback."""
=======
def sum_spend_column(df: pd.DataFrame, col: object) -> float:
    return float(df[col].apply(spend_cell_to_float).sum())


def detect_currency_symbols_in_column(df: pd.DataFrame, col: object, sample: int = 80) -> Optional[str]:
    if col is None or col not in df.columns:
        return None
    for val in df[col].head(sample):
        s = str(val)
        for sym, code in _SYMBOL_CURRENCY_PAIRS:
            if sym in s and code in VALID_ISO_CODES:
                return code
        if "¥" in s:
            digits = re.sub(r"[^\d]", "", s)
            if digits:
                n = int(digits[:12]) if digits else 0
                return "JPY" if n >= 1000 else "CNY"
        if re.match(r"^\s*R\s*[\d]", s, re.IGNORECASE) and "RM" not in s.upper():
            return "ZAR"
    return None


def detect_currency_and_spend_column(df: pd.DataFrame) -> Tuple[str, Optional[str], Optional[str]]:
    for col in df.columns:
        name = str(col)
        m = _RE_PARENS_CURRENCY.search(name)
        if m:
            code = m.group(1)
            if code in VALID_ISO_CODES:
                return code, col, None
    spend_guess = find_fallback_spend_column(df)
    sym = detect_currency_symbols_in_column(df, spend_guess) if spend_guess is not None else None
    if sym:
        return sym, spend_guess, None
    return "USD", spend_guess, CURRENCY_DEFAULT_USD_NOTICE


def find_fallback_spend_column(df: pd.DataFrame) -> Optional[str]:
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    for col in df.columns:
        low = str(col).lower()
        if "amount spent" in low or "spend" in low:
            return col
    return None


def get_spend_threshold(currency_code: str) -> float:
<<<<<<< HEAD
    """Use configured threshold or hardcoded fallback of 5 in detected currency."""
=======
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    return float(CURRENCY_THRESHOLDS.get(currency_code.upper(), 5))


def is_report_date_column(col_name: str) -> bool:
<<<<<<< HEAD
    """Case-insensitive: Reporting starts/ends, Date, or Day (substring match per spec)."""
=======
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    n = str(col_name).lower()
    if "reporting starts" in n or "reporting ends" in n:
        return True
    if "date" in n:
        return True
    if "day" in n:
        return True
    return False


def compute_report_date_span_days(df: pd.DataFrame) -> Optional[int]:
<<<<<<< HEAD
    """
    Min/max dates across all matching columns; total_days = (max - min) + 1.
    Returns None if no parseable dates found (caller skips the <3-day rule).
    """
    series_list: list[pd.Series] = []
=======
    series_list: List[pd.Series] = []
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    for col in df.columns:
        if not is_report_date_column(str(col)):
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        parsed = parsed.dropna()
        if not parsed.empty:
            series_list.append(parsed)
<<<<<<< HEAD

    if not series_list:
        return None

    all_ts = pd.concat(series_list, ignore_index=True)
    if all_ts.empty:
        return None

=======
    if not series_list:
        return None
    all_ts = pd.concat(series_list, ignore_index=True)
    if all_ts.empty:
        return None
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    min_d = pd.Timestamp(all_ts.min()).normalize().date()
    max_d = pd.Timestamp(all_ts.max()).normalize().date()
    return (max_d - min_d).days + 1


def dataframe_to_text(df: pd.DataFrame) -> str:
<<<<<<< HEAD
    """Convert DataFrame to plain text for LLM input."""
    return df.to_csv(index=False)


def split_for_telegram(text: str, max_len: int = MAX_TELEGRAM_MESSAGE_LEN) -> list[str]:
    """
    Split into <= max_len Telegram messages. Prefer paragraph breaks (\\n\\n), then single
    newlines, then spaces — never split mid-word; avoid mid-line splits when possible.
    """
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    rest = text

=======
    return df.to_csv(index=False)


def build_report_summary(
    df: pd.DataFrame,
    currency_code: str,
    total_spend: float,
    spend_col: str,
    day_span: Optional[int],
) -> str:
    col_sample = [str(c) for c in df.columns[:15]]
    rows = len(df)
    span = str(day_span) if day_span is not None else "unknown"
    return (
        f"Currency: {currency_code}\n"
        f"Rows: {rows}\n"
        f"Date span (days): {span}\n"
        f"Total spend (column {spend_col!s}): {total_spend}\n"
        f"Columns (first 15): {', '.join(col_sample)}"
    )


def split_for_telegram(text: str, max_len: int = MAX_TELEGRAM_MESSAGE_LEN) -> List[str]:
    text = text.strip()
    if len(text) <= max_len:
        return [text]
    chunks: List[str] = []
    rest = text
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    while rest:
        if len(rest) <= max_len:
            chunks.append(rest)
            break
<<<<<<< HEAD

        window = rest[:max_len]

=======
        window = rest[:max_len]
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
        idx_para = window.rfind("\n\n")
        if idx_para != -1:
            split_at = idx_para + 2
            piece = rest[:split_at].rstrip()
            if piece:
                chunks.append(piece)
                rest = rest[split_at:].lstrip()
                continue
<<<<<<< HEAD

=======
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
        idx_nl = window.rfind("\n")
        if idx_nl != -1:
            split_at = idx_nl + 1
            piece = rest[:split_at].rstrip()
            if piece:
                chunks.append(piece)
                rest = rest[split_at:].lstrip()
                continue
<<<<<<< HEAD

=======
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
        idx_sp = window.rfind(" ")
        if idx_sp != -1:
            split_at = idx_sp + 1
            piece = rest[:split_at].rstrip()
            if piece:
                chunks.append(piece)
                rest = rest[split_at:].lstrip()
                continue
<<<<<<< HEAD

        chunks.append(rest[:max_len])
        rest = rest[max_len:].lstrip()

    return chunks


def call_deepseek(report_text: str, currency_code: str) -> str:
    """Send report text to DeepSeek and return the recommendation."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is missing in environment.")

=======
        chunks.append(rest[:max_len])
        rest = rest[max_len:].lstrip()
    return chunks


def call_deepseek_messages(messages: List[Dict[str, str]]) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is missing in environment.")
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        traceback.print_exc()
        logger.exception("DeepSeek API timed out after %s seconds", DEEPSEEK_TIMEOUT_SECONDS)
        raise TimeoutError(ANALYSIS_TIMEOUT_TEXT) from exc
    except requests.RequestException as exc:
        traceback.print_exc()
        logger.exception("DeepSeek API request failed: %s", exc)
        raise RuntimeError("DeepSeek API request failed.") from exc
    try:
        data = response.json()
    except ValueError as exc:
        traceback.print_exc()
        logger.exception("DeepSeek returned non-JSON body")
        raise RuntimeError("DeepSeek API returned invalid JSON.") from exc
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        traceback.print_exc()
        logger.exception("DeepSeek response JSON missing expected fields: %s", exc)
        raise RuntimeError("DeepSeek response format was invalid.") from exc
    return str(content).strip()


def build_chat_messages(record: Dict[str, Any], user_text: str) -> List[Dict[str, str]]:
    ctx_parts: List[str] = []
    summ = (record.get("last_report_summary") or "").strip()
    analysis = (record.get("last_analysis") or "").strip()
    cur = (record.get("currency") or "").strip()
    if cur:
        ctx_parts.append(f"User currency context (if known): {cur}")
    if summ:
        ctx_parts.append("Last report summary:\n" + summ)
    if analysis:
        ctx_parts.append("Last full analysis (reference when user asks about the report):\n" + analysis)
    ctx = "\n\n".join(ctx_parts)
    system_full = ADLEY_SYSTEM_PROMPT
    if ctx:
        system_full += "\n\n---\n" + ctx
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_full}]
    for m in record.get("messages") or []:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = m.get("content")
        if role not in ("user", "assistant") or not isinstance(content, str):
            continue
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text})
    return messages


def call_deepseek_report_analysis(report_text: str, currency_code: str) -> str:
    system = ADLEY_SYSTEM_PROMPT + "\n\n" + ADLEY_ANALYSIS_FORMAT_PROMPT
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    user_prompt = (
        f"Report currency: {currency_code}\n\n"
        "Here is the Meta Ads report data as text:\n"
        f"{report_text}"
    )
<<<<<<< HEAD

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        print(f"[DeepSeek] Request timed out after {DEEPSEEK_TIMEOUT_SECONDS}s: {exc!s}")
        traceback.print_exc()
        logger.exception("DeepSeek API timed out after %s seconds", DEEPSEEK_TIMEOUT_SECONDS)
        raise TimeoutError(ANALYSIS_TIMEOUT_TEXT) from exc
    except requests.RequestException as exc:
        print(f"[DeepSeek] HTTP / network error: {exc!s}")
        traceback.print_exc()
        logger.exception("DeepSeek API request failed: %s", exc)
        raise RuntimeError("DeepSeek API request failed.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        print(f"[DeepSeek] Invalid JSON in response body: {exc!s}")
        traceback.print_exc()
        logger.exception("DeepSeek returned non-JSON body")
        raise RuntimeError("DeepSeek API returned invalid JSON.") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        print(f"[DeepSeek] Unexpected response shape: {data!r}")
        traceback.print_exc()
        logger.exception("DeepSeek response JSON missing expected fields: %s", exc)
        raise RuntimeError("DeepSeek response format was invalid.") from exc

    return str(content).strip()


def call_deepseek_followup(report_summary: str, last_analysis: str, question: str) -> str:
    """Ask DeepSeek a follow-up using stored report summary and prior analysis."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is missing in environment.")

    user_prompt = (
        "Report summary:\n"
        f"{report_summary}\n\n"
        "Original analysis:\n"
        f"{last_analysis}\n\n"
        "User follow-up question:\n"
        f"{question}"
    )

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": FOLLOW_UP_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout as exc:
        print(f"[DeepSeek follow-up] timed out after {DEEPSEEK_TIMEOUT_SECONDS}s: {exc!s}")
        traceback.print_exc()
        logger.exception("DeepSeek follow-up timed out")
        raise TimeoutError(ANALYSIS_TIMEOUT_TEXT) from exc
    except requests.RequestException as exc:
        print(f"[DeepSeek follow-up] HTTP error: {exc!s}")
        traceback.print_exc()
        logger.exception("DeepSeek follow-up request failed: %s", exc)
        raise RuntimeError("DeepSeek follow-up request failed.") from exc

    try:
        data = response.json()
    except ValueError as exc:
        print(f"[DeepSeek follow-up] invalid JSON: {exc!s}")
        traceback.print_exc()
        logger.exception("DeepSeek follow-up non-JSON body")
        raise RuntimeError("DeepSeek follow-up returned invalid JSON.") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        print(f"[DeepSeek follow-up] bad response shape: {data!r}")
        traceback.print_exc()
        logger.exception("DeepSeek follow-up missing fields: %s", exc)
        raise RuntimeError("DeepSeek follow-up response format invalid.") from exc

    return str(content).strip()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    text = START_MESSAGE_MARKDOWN_V2.replace("/help", "\\/help")
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    raw = HELP_TEXT.replace("/help", "\\/help").replace("/start", "\\/start")
    await reply_plain_markdown_v2(update.message, raw)


def read_report_dataframe(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    """Read CSV/XLSX into a DataFrame according to the PRD rules."""
    lower_name = file_name.lower()
    buffer = io.BytesIO(file_bytes)

    if lower_name.endswith(".csv"):
        return pd.read_csv(buffer, encoding="utf-8-sig")

    if lower_name.endswith(".xlsx"):
        df = pd.read_excel(buffer, sheet_name=0, engine="openpyxl")
        if df.empty or df.dropna(how="all").empty:
            raise ValueError(FIRST_SHEET_EMPTY_TEXT)
        return df

    raise ValueError("UNSUPPORTED_FILE_TYPE")


async def typing_keepalive(bot, chat_id: int, stop_event: asyncio.Event) -> None:
    """Send Telegram typing indicator every ~4s until stop_event is set."""
=======
    return call_deepseek_messages(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]
    )


async def typing_keepalive(bot, chat_id: int, stop_event: asyncio.Event) -> None:
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    while not stop_event.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except Exception:
            logger.exception("send_chat_action failed for chat_id=%s", chat_id)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
            break
        except asyncio.TimeoutError:
            continue


<<<<<<< HEAD
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or message.document is None:
        return

=======
async def delete_message_safe(msg) -> None:
    try:
        await msg.delete()
    except BadRequest:
        pass


async def progressive_report_placeholder(bot, chat_id: int, message_id: int, done: asyncio.Event) -> None:
    """Edit one status message at 12s and 27s while waiting for report analysis. Cancel via done.set()."""
    try:
        try:
            await asyncio.wait_for(done.wait(), timeout=12.0)
            return
        except asyncio.TimeoutError:
            pass
        if done.is_set():
            return
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Crunching the numbers...")
        except Exception as exc:
            logger.warning("placeholder edit (crunching): %s", exc)
        try:
            await asyncio.wait_for(done.wait(), timeout=15.0)
            return
        except asyncio.TimeoutError:
            pass
        if done.is_set():
            return
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="Almost done...")
        except Exception as exc:
            logger.warning("placeholder edit (almost done): %s", exc)
    except asyncio.CancelledError:
        return


def read_report_dataframe(file_name: str, file_bytes: bytes) -> pd.DataFrame:
    lower_name = file_name.lower()
    buffer = io.BytesIO(file_bytes)
    if lower_name.endswith(".csv"):
        return pd.read_csv(buffer, encoding="utf-8-sig")
    if lower_name.endswith(".xlsx"):
        df = pd.read_excel(buffer, sheet_name=0, engine="openpyxl")
        if df.empty or df.dropna(how="all").empty:
            raise ValueError(FIRST_SHEET_EMPTY_TEXT)
        return df
    raise ValueError("UNSUPPORTED_FILE_TYPE")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return
    uid = update.effective_user.id
    welcome = START_WELCOME_RAW.strip().replace("/help", "\\/help")
    await reply_markdown_v2(update.message, escape_markdown_v2(welcome))
    rec = await load_user(uid)
    append_message(rec, "user", "/start")
    append_message(rec, "assistant", START_WELCOME_RAW.strip())
    await save_user(uid, rec)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return
    uid = update.effective_user.id
    raw = HELP_TEXT.replace("/help", "\\/help").replace("/start", "\\/start")
    await reply_plain_markdown_v2(update.message, raw)
    rec = await load_user(uid)
    append_message(rec, "user", "/help")
    append_message(rec, "assistant", "Sent step-by-step Meta export instructions.")
    await save_user(uid, rec)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_user is None:
        return
    uid = update.effective_user.id
    rec = await load_user(uid)
    rec["messages"] = []
    await save_user(uid, rec)
    await reply_plain_markdown_v2(update.message, RESET_CONFIRM_TEXT)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or message.document is None or update.effective_user is None:
        return
    uid = update.effective_user.id
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    doc = message.document
    file_name = doc.file_name or "report"
    lower_name = file_name.lower()

    if not (lower_name.endswith(".csv") or lower_name.endswith(".xlsx")):
        await reply_plain_markdown_v2(message, "Please send a CSV (.csv) or Excel (.xlsx) report file.")
        return
<<<<<<< HEAD

=======
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    if doc.file_size and doc.file_size > MAX_FILE_SIZE_BYTES:
        await reply_plain_markdown_v2(message, FILE_TOO_LARGE_TEXT)
        return

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        file_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception:
<<<<<<< HEAD
=======
        traceback.print_exc()
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
        logger.exception("Failed to download file from Telegram.")
        await reply_plain_markdown_v2(message, "I could not download that file. Please try again.")
        return

    try:
        df = await asyncio.to_thread(read_report_dataframe, file_name, file_bytes)
    except pd.errors.EmptyDataError:
        await reply_plain_markdown_v2(message, "The file is empty. Please export your report again and resend it.")
        return
    except ValueError as exc:
        if str(exc) == "UNSUPPORTED_FILE_TYPE":
            await reply_plain_markdown_v2(message, "Please send a CSV (.csv) or Excel (.xlsx) report file.")
        elif str(exc) == FIRST_SHEET_EMPTY_TEXT:
            await reply_plain_markdown_v2(message, FIRST_SHEET_EMPTY_TEXT)
        else:
            await reply_plain_markdown_v2(message, "I could not read that file. Please check the export and try again.")
        return
    except Exception:
<<<<<<< HEAD
=======
        traceback.print_exc()
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
        logger.exception("Unexpected file parsing error.")
        await reply_plain_markdown_v2(message, "I could not read that file. Please check the export and try again.")
        return

    if df.empty:
        await reply_plain_markdown_v2(message, "The file has no rows to analyze. Please export and resend.")
        return

<<<<<<< HEAD
    await reply_plain_markdown_v2(message, "Analyzing your report. This may take up to a minute.")
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(
        typing_keepalive(context.bot, message.chat_id, stop_typing)
    )
    try:
        currency_code, spend_col, currency_notice = detect_currency_and_spend_column(df)
        if spend_col is None:
            spend_col = find_fallback_spend_column(df)
        if spend_col is None:
            await reply_plain_markdown_v2(
                message,
                "I could not find a spend column in this report. Please export using Meta 'Performance and Clicks' columns and resend.",
            )
            return

        total_spend = sum_spend_column(df, spend_col)
        day_span = compute_report_date_span_days(df)
        threshold = get_spend_threshold(currency_code)

        print(f"DEBUG: detected_currency={currency_code}")
        print(f"DEBUG: spend_column={spend_col!s}")
        print(f"DEBUG: total_spend={total_spend}")
        print(f"DEBUG: total_days={day_span}")
        print(f"DEBUG: threshold={threshold}")

        if currency_notice:
            await reply_plain_markdown_v2(message, currency_notice)

        below_spend = total_spend < threshold
        below_days = day_span is not None and day_span < 3

        if below_spend or below_days:
            await reply_plain_markdown_v2(message, NOT_ENOUGH_DATA_TEXT)
            return

        report_text = dataframe_to_text(df)
        if not report_text.strip():
            await reply_plain_markdown_v2(message, "The file content looks empty after parsing. Please export and resend.")
            return

        try:
            recommendation = await asyncio.to_thread(call_deepseek, report_text, currency_code)
        except TimeoutError:
            traceback.print_exc()
            logger.exception("DeepSeek analysis timed out (user shown ANALYSIS_TIMEOUT_TEXT)")
=======
    rec = await load_user(uid)
    currency_code, spend_col, currency_notice = detect_currency_and_spend_column(df)
    if spend_col is None:
        spend_col = find_fallback_spend_column(df)
    if spend_col is None:
        await reply_plain_markdown_v2(
            message,
            "I could not find a spend column in this report. Please export using Meta 'Performance and Clicks' columns and resend.",
        )
        return

    total_spend = sum_spend_column(df, spend_col)
    day_span = compute_report_date_span_days(df)
    threshold = get_spend_threshold(currency_code)

    if currency_notice:
        await reply_plain_markdown_v2(message, currency_notice)

    below_spend = total_spend < threshold
    below_days = day_span is not None and day_span < 3
    if below_spend or below_days:
        await reply_plain_markdown_v2(message, NOT_ENOUGH_DATA_TEXT)
        return

    report_text = dataframe_to_text(df)
    if not report_text.strip():
        await reply_plain_markdown_v2(message, "The file content looks empty after parsing. Please export and resend.")
        return

    status_msg = await message.reply_text("Reading your report...")
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_keepalive(context.bot, message.chat_id, stop_typing))
    done_prog = asyncio.Event()
    prog_task = asyncio.create_task(
        progressive_report_placeholder(context.bot, message.chat_id, status_msg.message_id, done_prog)
    )
    try:
        try:
            recommendation = await asyncio.to_thread(call_deepseek_report_analysis, report_text, currency_code)
        except TimeoutError:
            traceback.print_exc()
            logger.exception("DeepSeek analysis timed out")
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
            await reply_plain_markdown_v2(message, ANALYSIS_TIMEOUT_TEXT)
            return
        except Exception as exc:
            traceback.print_exc()
            logger.exception("DeepSeek analysis failed: %s", exc)
            await reply_plain_markdown_v2(message, "I could not complete analysis right now. Please try again shortly.")
            return

        report_summary = build_report_summary(df, currency_code, total_spend, spend_col, day_span)
<<<<<<< HEAD
        full_out = recommendation + ANALYSIS_FOLLOW_UP_FOOTER
        escaped = escape_markdown_v2(full_out)
        for chunk in split_for_telegram(escaped):
            await reply_markdown_v2(message, chunk)

        user = update.effective_user
        if user:
            user_sessions[user.id] = {
                "last_analysis": recommendation,
                "report_summary": report_summary,
                "follow_ups_remaining": 3,
            }
=======
        rec["last_analysis"] = recommendation
        rec["last_report_summary"] = report_summary
        rec["currency"] = currency_code
        append_message(rec, "user", "User uploaded a report. Adley analyzed it.")
        await save_user(uid, rec)

        if "want me to break down a specific ad set" in recommendation.lower():
            out_plain = recommendation
        else:
            out_plain = recommendation + ANALYSIS_FOOTER_PLAIN
        escaped = escape_markdown_v2(out_plain)
        for chunk in split_for_telegram(escaped):
            await reply_markdown_v2(message, chunk)
    finally:
        done_prog.set()
        prog_task.cancel()
        try:
            await prog_task
        except asyncio.CancelledError:
            pass
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        await delete_message_safe(status_msg)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or not message.text or update.effective_user is None:
        return
    uid = update.effective_user.id
    user_text = message.text.strip()
    rec = await load_user(uid)
    messages = build_chat_messages(rec, user_text)

    thinking_msg = await message.reply_text("One sec...")
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_keepalive(context.bot, message.chat_id, stop_typing))
    try:
        try:
            reply = await asyncio.to_thread(call_deepseek_messages, messages)
        except TimeoutError:
            traceback.print_exc()
            logger.exception("DeepSeek chat timed out")
            append_message(rec, "user", user_text)
            await save_user(uid, rec)
            await reply_plain_markdown_v2(message, ANALYSIS_TIMEOUT_TEXT)
            return
        except Exception as exc:
            traceback.print_exc()
            logger.exception("DeepSeek chat failed: %s", exc)
            append_message(rec, "user", user_text)
            await save_user(uid, rec)
            await reply_plain_markdown_v2(message, "I could not answer that right now. Please try again shortly.")
            return

        append_message(rec, "user", user_text)
        append_message(rec, "assistant", reply)
        await save_user(uid, rec)

        escaped = escape_markdown_v2(reply)
        for chunk in split_for_telegram(escaped):
            await reply_markdown_v2(message, chunk)
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    finally:
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
<<<<<<< HEAD


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Follow-up questions (up to 3) or prompt to send a report."""
    message = update.message
    if message is None or not message.text:
        return

    user = update.effective_user
    if user is None:
        return

    uid = user.id
    if uid not in user_sessions:
        await reply_plain_markdown_v2(message, MSG_NO_SESSION)
        return

    sess = user_sessions[uid]
    if sess.get("follow_ups_remaining", 0) <= 0:
        await reply_plain_markdown_v2(message, MSG_FOLLOW_UPS_EXHAUSTED)
        return

    try:
        reply = await asyncio.to_thread(
            call_deepseek_followup,
            sess["report_summary"],
            sess["last_analysis"],
            message.text.strip(),
        )
    except TimeoutError:
        traceback.print_exc()
        logger.exception("DeepSeek follow-up timed out")
        await reply_plain_markdown_v2(message, ANALYSIS_TIMEOUT_TEXT)
        return
    except Exception as exc:
        traceback.print_exc()
        logger.exception("DeepSeek follow-up failed: %s", exc)
        await reply_plain_markdown_v2(message, "I could not answer that right now. Please try again shortly.")
        return

    sess["follow_ups_remaining"] -= 1
    rem = sess["follow_ups_remaining"]
    escaped = escape_markdown_v2(reply) + "\n\n" + escape_markdown_v2_plain(f"Follow-ups remaining: {rem}.")
    for chunk in split_for_telegram(escaped):
        await reply_markdown_v2(message, chunk)
=======
        await delete_message_safe(thinking_msg)
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
<<<<<<< HEAD
            BotCommand("start", "Welcome and instructions"),
            BotCommand("help", "How to export your Meta ad report"),
=======
            BotCommand("start", "Welcome from Adley"),
            BotCommand("help", "Meta report export steps"),
            BotCommand("reset", "Clear conversation, keep last report"),
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
        ]
    )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in environment.")
<<<<<<< HEAD

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Ad Decision Bot is running...")
=======
    ensure_data_dir_and_file_sync()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Adley is running...")
>>>>>>> b59707a957a3e8186dce3440d4af2cbb319ebc31
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
