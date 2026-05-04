import asyncio
import io
import logging
import os
import re
import traceback
from typing import Optional

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


load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()

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

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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
    """Escape plain user-facing copy and send as MarkdownV2."""
    await reply_markdown_v2(message, escape_markdown_v2_plain(plain_text))


def spend_cell_to_float(value: object) -> float:
    """Parse a spend cell; empty, NaN, or dash-like values count as 0."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0

    text = str(value).strip()
    if text in {"", "-", "—", "--", "–", "N/A", "n/a", "NA", "NaN"}:
        return 0.0

    text = text.replace(",", "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if text in {"", "-", ".", "-."}:
        return 0.0

    try:
        return float(text)
    except ValueError:
        return 0.0


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
    for col in df.columns:
        low = str(col).lower()
        if "amount spent" in low or "spend" in low:
            return col
    return None


def get_spend_threshold(currency_code: str) -> float:
    """Use configured threshold or hardcoded fallback of 5 in detected currency."""
    return float(CURRENCY_THRESHOLDS.get(currency_code.upper(), 5))


def is_report_date_column(col_name: str) -> bool:
    """Case-insensitive: Reporting starts/ends, Date, or Day (substring match per spec)."""
    n = str(col_name).lower()
    if "reporting starts" in n or "reporting ends" in n:
        return True
    if "date" in n:
        return True
    if "day" in n:
        return True
    return False


def compute_report_date_span_days(df: pd.DataFrame) -> Optional[int]:
    """
    Min/max dates across all matching columns; total_days = (max - min) + 1.
    Returns None if no parseable dates found (caller skips the <3-day rule).
    """
    series_list: list[pd.Series] = []
    for col in df.columns:
        if not is_report_date_column(str(col)):
            continue
        parsed = pd.to_datetime(df[col], errors="coerce")
        parsed = parsed.dropna()
        if not parsed.empty:
            series_list.append(parsed)

    if not series_list:
        return None

    all_ts = pd.concat(series_list, ignore_index=True)
    if all_ts.empty:
        return None

    min_d = pd.Timestamp(all_ts.min()).normalize().date()
    max_d = pd.Timestamp(all_ts.max()).normalize().date()
    return (max_d - min_d).days + 1


def dataframe_to_text(df: pd.DataFrame) -> str:
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

    while rest:
        if len(rest) <= max_len:
            chunks.append(rest)
            break

        window = rest[:max_len]

        idx_para = window.rfind("\n\n")
        if idx_para != -1:
            split_at = idx_para + 2
            piece = rest[:split_at].rstrip()
            if piece:
                chunks.append(piece)
                rest = rest[split_at:].lstrip()
                continue

        idx_nl = window.rfind("\n")
        if idx_nl != -1:
            split_at = idx_nl + 1
            piece = rest[:split_at].rstrip()
            if piece:
                chunks.append(piece)
                rest = rest[split_at:].lstrip()
                continue

        idx_sp = window.rfind(" ")
        if idx_sp != -1:
            split_at = idx_sp + 1
            piece = rest[:split_at].rstrip()
            if piece:
                chunks.append(piece)
                rest = rest[split_at:].lstrip()
                continue

        chunks.append(rest[:max_len])
        rest = rest[max_len:].lstrip()

    return chunks


def call_deepseek(report_text: str, currency_code: str) -> str:
    """Send report text to DeepSeek and return the recommendation."""
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY is missing in environment.")

    user_prompt = (
        f"Report currency: {currency_code}\n\n"
        "Here is the Meta Ads report data as text:\n"
        f"{report_text}"
    )

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


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or message.document is None:
        return

    doc = message.document
    file_name = doc.file_name or "report"
    lower_name = file_name.lower()

    if not (lower_name.endswith(".csv") or lower_name.endswith(".xlsx")):
        await reply_plain_markdown_v2(message, "Please send a CSV (.csv) or Excel (.xlsx) report file.")
        return

    if doc.file_size and doc.file_size > MAX_FILE_SIZE_BYTES:
        await reply_plain_markdown_v2(message, FILE_TOO_LARGE_TEXT)
        return

    try:
        tg_file = await context.bot.get_file(doc.file_id)
        file_bytes = bytes(await tg_file.download_as_bytearray())
    except Exception:
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
        logger.exception("Unexpected file parsing error.")
        await reply_plain_markdown_v2(message, "I could not read that file. Please check the export and try again.")
        return

    if df.empty:
        await reply_plain_markdown_v2(message, "The file has no rows to analyze. Please export and resend.")
        return

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
            await reply_plain_markdown_v2(message, ANALYSIS_TIMEOUT_TEXT)
            return
        except Exception as exc:
            traceback.print_exc()
            logger.exception("DeepSeek analysis failed: %s", exc)
            await reply_plain_markdown_v2(message, "I could not complete analysis right now. Please try again shortly.")
            return

        report_summary = build_report_summary(df, currency_code, total_spend, spend_col, day_span)
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
    finally:
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass


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


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Welcome and instructions"),
            BotCommand("help", "How to export your Meta ad report"),
        ]
    )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in environment.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Ad Decision Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
