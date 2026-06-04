"""
channel_tracker.py — The brain of OUTER AGOGE Bot.

Monitors all messages passively. No commands needed.
Detects channel type and acts accordingly.
"""

import re
import logging
from typing import Optional
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    register_member, get_channel_type, display_name, get_member,
    log_gm, get_gm_streak,
    log_report, get_report_streak,
    log_fitness,
    submit_money_in, get_money_in,
    MONTHS
)

logger = logging.getLogger(__name__)


# ─── MONEY EXTRACTION ──────────────────────────────────────────────────────────

def extract_money_amount(text: str) -> Optional[float]:
    """
    Intelligently extract a money amount from any message format.
    Handles: $1,300 | $1.3k | 1300$ | Amount: 1300 | 1300 USD | €500 | 1.3K
    Returns the highest amount found (most likely the relevant win).
    """
    amounts = []
    text_lower = text.lower()

    # Pattern groups: (regex, multiplier)
    patterns = [
        # $1.3k / $1.3K
        (r'\$\s*([\d,]+(?:\.\d+)?)\s*[kK]\b', 1000),
        # $1,300 / $1300
        (r'\$\s*([\d,]+(?:\.\d+)?)', 1),
        # 1.3k$ / 1300$
        (r'\b([\d,]+(?:\.\d+)?)\s*[kK]\s*\$', 1000),
        (r'\b([\d,]+(?:\.\d+)?)\s*\$', 1),
        # €500 / €1.3k
        (r'€\s*([\d,]+(?:\.\d+)?)\s*[kK]\b', 1000),
        (r'€\s*([\d,]+(?:\.\d+)?)', 1),
        # 1.3k USD/EUR/GBP
        (r'\b([\d,]+(?:\.\d+)?)\s*[kK]\s*(?:usd|eur|gbp|dollars?|euros?)\b', 1000),
        (r'\b([\d,]+(?:\.\d+)?)\s*(?:usd|eur|gbp|dollars?|euros?)\b', 1),
        # keyword: $amount or keyword: amount
        (r'(?:amount|made|earned|closed|revenue|collected|deal|client|payment|paid|sale|profit)[:\s]+\$?\s*([\d,]+(?:\.\d+)?)\s*[kK]\b', 1000),
        (r'(?:amount|made|earned|closed|revenue|collected|deal|client|payment|paid|sale|profit)[:\s]+\$?\s*([\d,]+(?:\.\d+)?)', 1),
    ]

    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, text_lower):
            try:
                num_str = match.group(1).replace(',', '')
                amount = float(num_str) * multiplier
                if 1 <= amount <= 10_000_000:  # sanity range
                    amounts.append(amount)
            except (ValueError, IndexError):
                continue

    return max(amounts) if amounts else None


# ─── MAIN HANDLER ──────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Called on every group message. Checks the channel and acts accordingly."""

    msg = update.message
    if not msg or not msg.from_user:
        return

    # Skip commands — those are handled by CommandHandlers
    if msg.text and msg.text.startswith("/"):
        return

    user      = msg.from_user
    chat_id   = msg.chat_id
    thread_id = msg.message_thread_id  # None if not a forum topic
    text      = msg.text or msg.caption or ""

    # Auto-register member
    register_member(
        user.id,
        user.username or "",
        user.first_name or user.username or "Spartan"
    )

    # Determine which channel this message is in
    channel_type = get_channel_type(chat_id, thread_id)

    if channel_type is None:
        return  # Not a monitored channel — ignore

    # ── Route to the right handler ──────────────────────────────────────────

    if channel_type == "gm":
        await _handle_gm(update, context, user)

    elif channel_type == "accountability":
        await _handle_accountability(update, context, user, text)

    elif channel_type == "business":
        await _handle_business(update, context, user, text)

    elif channel_type == "fitness":
        await _handle_fitness(update, context, user, text)

    elif channel_type == "lifestyle":
        # Track passively, no reply needed
        pass


# ─── CHANNEL HANDLERS ──────────────────────────────────────────────────────────

async def _handle_gm(update, context, user) -> None:
    """GM channel: just posting here counts as GM for the day."""
    is_new = log_gm(user.id)

    if is_new:
        streak = get_gm_streak(user.id)
        if streak in (7, 14, 21, 30) or (streak > 30 and streak % 30 == 0):
            await update.message.reply_text(
                f"☀️ *{streak} day GM streak* - {user.first_name}. Spartan standard.",
                parse_mode="Markdown"
            )
        # Otherwise: track silently. No reply needed.
    # If already logged today: completely silent.


async def _handle_accountability(update, context, user, text: str) -> None:
    """Accountability channel: posting here counts as the daily report."""
    is_new = log_report(user.id, text)
    streak = get_report_streak(user.id)

    if is_new and streak in (7, 14, 21, 30) or (streak > 30 and streak % 30 == 0):
        await update.message.reply_text(
            f"📋 *{streak} day report streak* - {user.first_name}. Consistent.",
            parse_mode="Markdown"
        )
    # Otherwise: track silently.


async def _handle_business(update, context, user, text: str) -> None:
    """
    Business Wins channel: try to extract a money amount from the post.
    If found: log it and confirm.
    If not found: prompt them to manually submit.
    """
    if not text:
        return

    today  = date.today()
    amount = extract_money_amount(text)

    if amount is not None:
        # Check if this would update an existing entry
        existing = get_money_in(user.id, today.month, today.year)
        submit_money_in(user.id, amount, today.month, today.year)

        if existing > 0 and existing != amount:
            msg = (
                f"💰 *${amount:,.0f}* logged for *{user.first_name}*.\n"
                f"_(Updated from ${existing:,.0f})_\n"
                f"Use /moneyin to correct if needed."
            )
        else:
            msg = (
                f"💰 *${amount:,.0f}* logged - *{MONTHS[today.month]} {today.year}*.\n"
                f"Use /moneyin to correct if needed."
            )
        await update.message.reply_text(msg, parse_mode="Markdown")

    else:
        # No amount detected — prompt for manual entry
        await update.message.reply_text(
            f"No amount detected, {user.first_name}.\n"
            f"Submit manually: /moneyin <amount>"
        )


async def _handle_fitness(update, context, user, text: str) -> None:
    """Fitness Wins channel: log the activity. Track silently."""
    log_fitness(user.id, text)
    # Silent tracking — no reply needed
