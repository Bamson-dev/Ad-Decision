"""
Adley — AI media buyer Telegram bot (Meta reports + conversational guidance).

Author: Bamidele Matthew
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiofiles
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

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
MAX_TELEGRAM_MESSAGE_LEN = 3500
DEEPSEEK_TIMEOUT_SECONDS = 90
MAX_HISTORY_MESSAGES = 20

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
    "Currency could not be auto-detected. Defaulting to USD."
)

RESET_CONFIRM_TEXT = (
    "Conversation reset. I still remember your last report. Ask me anything."
)

ANALYSIS_FOOTER_PLAIN = "\n\nAsk me anything about this report, or send another. I'm here to help."

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
You are Adley, a senior global media buyer with 15+ years of experience running Meta ads (Facebook and Instagram). You have managed over $50 million in ad spend across e-commerce, info products, lead generation, and local services. You have run ads across Africa, the US, UK, Europe, and Asia. You understand the Meta auction, creative strategy, audience targeting, bidding, attribution, scaling, and the difference between a winning ad set and a leaking one.
You speak like a senior buyer talking to a peer. Direct, confident, plain English, no fluff, no AI disclaimers, no "as an AI language model" or "I cannot" hedging. You answer like a real human consultant. You give clear, specific, actionable advice based on data and experience.
Your knowledge includes:

Akin Alabi's "How to Sell to Nigerians" framework: giant promise, free bonus, guarantee, proof, fear-based selling, awoof
Alex Hormozi's $100M Offers: value equation, offer stacking, risk reversal, scarcity, urgency
CPM reduction tactics: no ad-y language in first 3 lines, story-first hooks, pattern-break openings, delay the pitch
Nigerian market context: Naira pricing, Lagos and Abuja CPM benchmarks, OPay and Paystack pixel quirks, Pidgin copy when relevant
Global market context: USD, EUR, GBP benchmarks, e-commerce vs lead gen vs info product strategies

You are not a generic AI. You are Adley.
When analyzing reports:

Identify the campaign objective from the data and tailor advice
Reference real numbers and real ad set names from the report
Never invent data
Use benchmarks where useful: CTR above 1% is healthy for cold traffic, ROAS above 2x is generally profitable for e-commerce, frequency above 3 signals fatigue, climbing CPM signals declining relevance, rising CPL means audience saturation

When chatting:

Answer ad-related questions with specific advice and frameworks
If the user references their previous report, pull from the saved analysis
If the user asks something not related to ads, marketing, copywriting, funnels, audiences, creatives, or business growth, politely redirect: "I'm here for ad decisions, not general chat. Ask me anything about your ads, send a report, or tell me what's stuck and I'll help."
Use the user's preferred language. If they write in Pidgin, respond in Pidgin. Default to standard English.
Use the user's currency context if known.

Output formatting rules:

Use plain numbered lists with regular periods (1., 2., 3.). Do NOT use backslash escapes like 1. The bot's code will handle escaping for Telegram MarkdownV2.
Use single asterisks for section titles like SECTION NAME.
Use blank lines between sections and between numbered items for readability.
Use ISO currency codes (NGN, USD, GBP) instead of currency symbols.
Do not use markdown features other than single-asterisk bold.
Never invent numbers, prices, or facts. If you don't know, say so.

Speak like a real operator who's lived this. Confident, direct, useful.
""".strip()

ADLEY_ANALYSIS_FORMAT_PROMPT = """
When you analyze a Meta ad report, output plain text only (the app will escape for Telegram MarkdownV2). Follow this layout exactly (substitute real ad set names and numbers from the report only).

*QUICK TAKE*

Total spend: [ISO code] [amount] across [N] ads
Top performer: [ad set name] ([brief reason])
Biggest waste: [ad set name] ([brief reason])

*WHAT IS WASTING MONEY*

1. [Ad set name]: [reason with specific numbers from report]. Pause it.

2. [Ad set name]: [reason]. Pause it.

*WHAT IS WORKING*

1. [Ad set name]: [numbers]. Scale by [percent]. Increase budget from [current] to [new].

*WHAT TO FIX*

1. [Specific actionable change with numbers from report]

2. [Specific actionable change]

Rules: plain numbered lists with regular periods (1., 2., 3.) — never backslash escapes before the period. One blank line between sections and between numbered items. ISO currency codes only, no symbols. Under 4000 characters when possible. End with: Ask me anything about this report, or send another. I'm here to help.
""".strip()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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
    text = text.replace("**", "*")
    text = re.sub(r"(?<=\d)\\(?=\.)", "", text)
    parts: List[str] = []
    last = 0
    for m in re.finditer(r"\*([^*]+)\*", text):
        parts.append(escape_markdown_v2_plain(text[last : m.start()]))
        inner = m.group(1)
        parts.append("*" + escape_markdown_v2_plain(inner) + "*")
        last = m.end()
    parts.append(escape_markdown_v2_plain(text[last:]))
    return "".join(parts)


async def reply_markdown_v2(message, text: str) -> None:
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
    await reply_markdown_v2(message, escape_markdown_v2_plain(plain_text))


def spend_cell_to_float(value: object) -> float:
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
    for col in df.columns:
        low = str(col).lower()
        if "amount spent" in low or "spend" in low:
            return col
    return None


def get_spend_threshold(currency_code: str) -> float:
    return float(CURRENCY_THRESHOLDS.get(currency_code.upper(), 5))


def is_report_date_column(col_name: str) -> bool:
    n = str(col_name).lower()
    if "reporting starts" in n or "reporting ends" in n:
        return True
    if "date" in n:
        return True
    if "day" in n:
        return True
    return False


def compute_report_date_span_days(df: pd.DataFrame) -> Optional[int]:
    series_list: List[pd.Series] = []
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
    user_prompt = (
        f"Report currency: {currency_code}\n\n"
        "Here is the Meta Ads report data as text:\n"
        f"{report_text}"
    )
    return call_deepseek_messages(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ]
    )


async def typing_keepalive(bot, chat_id: int, stop_event: asyncio.Event) -> None:
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


async def delete_message_safe(msg) -> None:
    try:
        await msg.delete()
    except BadRequest:
        pass


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
    welcome = (
        "Hey, I'm Adley\n\n"
        "Your AI media buyer. I help you make sharper ad decisions.\n\n"
        "What I do\n\n"
        "• Read your Meta ad reports and tell you what to pause, scale, and fix\n"
        "• Answer any question about ads, copy, audiences, creatives, or scaling\n"
        "• Walk you through what's stuck and how to fix it\n\n"
        "How to use me\n\n"
        "Send your CSV or Excel report, or just type a question. Tap /help for export instructions.\n\n"
        "Ready when you are."
    )
    raw = welcome.replace("/help", "\\/help")
    await reply_plain_markdown_v2(update.message, raw)
    rec = await load_user(uid)
    append_message(rec, "user", "/start")
    append_message(rec, "assistant", welcome)
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
        traceback.print_exc()
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
        traceback.print_exc()
        logger.exception("Unexpected file parsing error.")
        await reply_plain_markdown_v2(message, "I could not read that file. Please check the export and try again.")
        return

    if df.empty:
        await reply_plain_markdown_v2(message, "The file has no rows to analyze. Please export and resend.")
        return

    rec = await load_user(uid)
    thinking_msg = await message.reply_text("Thinking...")
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(typing_keepalive(context.bot, message.chat_id, stop_typing))
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
            recommendation = await asyncio.to_thread(call_deepseek_report_analysis, report_text, currency_code)
        except TimeoutError:
            traceback.print_exc()
            logger.exception("DeepSeek analysis timed out")
            await reply_plain_markdown_v2(message, ANALYSIS_TIMEOUT_TEXT)
            return
        except Exception as exc:
            traceback.print_exc()
            logger.exception("DeepSeek analysis failed: %s", exc)
            await reply_plain_markdown_v2(message, "I could not complete analysis right now. Please try again shortly.")
            return

        report_summary = build_report_summary(df, currency_code, total_spend, spend_col, day_span)
        rec["last_analysis"] = recommendation
        rec["last_report_summary"] = report_summary
        rec["currency"] = currency_code
        append_message(rec, "user", "User uploaded a report. Adley analyzed it.")
        await save_user(uid, rec)

        if "Ask me anything about this report" in recommendation:
            out_plain = recommendation
        else:
            out_plain = recommendation + ANALYSIS_FOOTER_PLAIN
        escaped = escape_markdown_v2(out_plain)
        for chunk in split_for_telegram(escaped):
            await reply_markdown_v2(message, chunk)
    finally:
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        await delete_message_safe(thinking_msg)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or not message.text or update.effective_user is None:
        return
    uid = update.effective_user.id
    user_text = message.text.strip()
    rec = await load_user(uid)
    messages = build_chat_messages(rec, user_text)

    thinking_msg = await message.reply_text("Thinking...")
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
    finally:
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        await delete_message_safe(thinking_msg)


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Welcome from Adley"),
            BotCommand("help", "Meta report export steps"),
            BotCommand("reset", "Clear conversation, keep last report"),
        ]
    )


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing in environment.")
    ensure_data_dir_and_file_sync()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    logger.info("Adley is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
