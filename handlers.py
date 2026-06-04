"""
handlers.py — Command handlers for OUTER AGOGE Bot v2
Only admin actions and data viewing. Daily tracking is automatic.
"""

import os
import logging
from datetime import date
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    register_member, get_member_by_username, get_all_members, display_name,
    get_gm_streak, get_report_streak, get_gm_count_month, get_report_count_month,
    get_fitness_count_month, submit_money_in, get_leaderboard, remove_money_in,
    award_badge, get_member_badges, get_hall_of_record,
    post_challenge, get_active_challenge, complete_challenge,
    register_channel, get_all_channel_config, MONTHS, VALID_CHANNEL_TYPES
)

logger = logging.getLogger(__name__)

BADGE_EMOJI = {
    "CONQUEROR": "🩸",
    "GLADIATOR": "🩸",
}
BADGE_DISPLAY = {
    "CONQUEROR": "CONQUEROR",
    "GLADIATOR": "GLADIATOR",
}
VALID_BADGES = list(BADGE_EMOJI.keys())

CHANNEL_LABELS = {
    "gm":             "GM ☀️",
    "accountability": "Accountability 📋",
    "business":       "Business Wins 💰",
    "fitness":        "Fitness Wins 💪",
    "lifestyle":      "Lifestyle Wins 🌍",
}


# ─── HELPERS ───────────────────────────────────────────────────────────────────

def get_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def is_admin(telegram_id: int) -> bool:
    return telegram_id in get_admin_ids()


def auto_register(update: Update) -> None:
    u = update.effective_user
    register_member(u.id, u.username or "", u.first_name or u.username or "Spartan")


def leaderboard_text(month: int, year: int, suffix: str = "") -> str:
    rows = get_leaderboard(month, year)
    if not rows:
        return "No members registered yet."

    medals = ["🥇", "🥈", "🥉"]
    lines, total = [], 0.0

    for i, row in enumerate(rows):
        name   = row["name"] or row["username"] or "Spartan"
        amount = row["amount"] or 0.0
        total += amount

        if amount > 0 and i < 3:
            emoji = medals[i]
        elif amount > 0:
            emoji = "🟢"
        else:
            emoji = "🔴"

        amt_str = f"${amount:,.0f}" if amount > 0 else "$0"
        lines.append(f"{emoji} {name} - {amt_str}")

    avg        = total / len(rows)
    month_name = MONTHS[month].upper()
    title      = f"{month_name} MONEY-IN{f' - {suffix}' if suffix else ''}"

    return (
        f"🩸 *{title}* 🩸\n"
        f"——————————————\n"
        + "\n".join(lines) + "\n"
        f"——————————————\n"
        f"*Total: ${total:,.0f}*\n"
        f"*Group Average: ${avg:,.0f}*"
    )


# ─── SETUP ─────────────────────────────────────────────────────────────────────

async def cmd_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only. 🩸")
        return

    if not context.args:
        configs = get_all_channel_config(update.message.chat_id)
        if not configs:
            await update.message.reply_text(
                "*No channels configured yet.*\n\n"
                "Run inside each topic:\n\n"
                "/setup gm\n"
                "/setup accountability\n"
                "/setup business\n"
                "/setup fitness\n"
                "/setup lifestyle",
                parse_mode="Markdown"
            )
        else:
            lines = [f"✅ {CHANNEL_LABELS.get(c['channel_type'], c['channel_type'])} — thread {c['thread_id']}" for c in configs]
            await update.message.reply_text(
                "*🩸 Channel Configuration:*\n\n" + "\n".join(lines),
                parse_mode="Markdown"
            )
        return

    channel_type = context.args[0].lower()
    if channel_type not in VALID_CHANNEL_TYPES:
        await update.message.reply_text(
            f"Invalid type. Choose: {', '.join(VALID_CHANNEL_TYPES)}"
        )
        return

    chat_id   = update.message.chat_id
    thread_id = update.message.message_thread_id

    register_channel(chat_id, thread_id, channel_type)

    label = CHANNEL_LABELS.get(channel_type, channel_type)
    await update.message.reply_text(
        f"✅ *{label}* registered.\n"
        f"All messages here are now tracked automatically.",
        parse_mode="Markdown"
    )


# ─── VIEWING COMMANDS ──────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_register(update)
    admin_section = ""
    if is_admin(update.effective_user.id):
        admin_section = (
            "\n*Admin:*\n"
            "/setup <type> — Register a topic channel\n"
            "/badge @user CONQUEROR|GLADIATOR\n"
            "/challenge <description>\n"
            "/winner @user\n"
            "/removemoneyin @user\n"
        )

    await update.message.reply_text(
        "*🩸 OUTER AGOGE Bot*\n\n"
        "_Post in the right channel. Bot handles the rest._\n\n"
        "📊 *Commands:*\n"
        "/lb — Money-in leaderboard\n"
        "/streak — All Spartan streaks\n"
        "/mystats — Your stats\n"
        "/hall — Hall of Record\n"
        "/members — All Spartans\n"
        "/moneyin <amount> — Manual money-in\n"
        f"{admin_section}",
        parse_mode="Markdown"
    )


async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_register(update)
    today = date.today()
    await update.message.reply_text(
        leaderboard_text(today.month, today.year),
        parse_mode="Markdown"
    )


async def cmd_streak(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_register(update)
    members = get_all_members()

    if not members:
        await update.message.reply_text("No Spartans registered yet.")
        return

    lines = []
    for m in members:
        gm_s  = get_gm_streak(m["telegram_id"])
        rep_s = get_report_streak(m["telegram_id"])
        name  = display_name(m)
        gm_e  = "🔥" if gm_s >= 7 else ("✅" if gm_s >= 1 else "⬜")
        rep_e = "🔥" if rep_s >= 7 else ("✅" if rep_s >= 1 else "⬜")
        lines.append(
            f"*{name}*\n"
            f"  ☀️ GM {gm_e} {gm_s}d  |  📋 Report {rep_e} {rep_s}d"
        )

    await update.message.reply_text(
        "*🩸 SPARTAN STREAKS*\n——————————————\n" + "\n\n".join(lines),
        parse_mode="Markdown"
    )


async def cmd_mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_register(update)
    user  = update.effective_user
    today = date.today()

    gm_streak  = get_gm_streak(user.id)
    rep_streak = get_report_streak(user.id)
    gm_month   = get_gm_count_month(user.id, today.month, today.year)
    rep_month  = get_report_count_month(user.id, today.month, today.year)
    fit_month  = get_fitness_count_month(user.id, today.month, today.year)
    badges     = get_member_badges(user.id)

    badge_text = ""
    if badges:
        badge_lines = [
            f"🩸 {BADGE_DISPLAY.get(b['badge_type'], b['badge_type'])} - {MONTHS[b['month']]} {b['year']}"
            for b in badges
        ]
        badge_text = "\n\n*Titles:*\n" + "\n".join(badge_lines)

    name = user.first_name or "Spartan"
    await update.message.reply_text(
        f"*🩸 {name.upper()} - STATS*\n"
        f"——————————————\n"
        f"☀️ GM Streak: {gm_streak} days\n"
        f"📋 Report Streak: {rep_streak} days\n"
        f"GMs this month: {gm_month}\n"
        f"Reports this month: {rep_month}\n"
        f"💪 Fitness wins this month: {fit_month}"
        f"{badge_text}",
        parse_mode="Markdown"
    )


async def cmd_hall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_register(update)
    records = get_hall_of_record()

    if not records:
        await update.message.reply_text(
            "*🩸 HALL OF RECORD*\n\nEmpty. First titles await.",
            parse_mode="Markdown"
        )
        return

    lines = [
        f"🩸 *{BADGE_DISPLAY.get(r['badge_type'], r['badge_type'])}*\n"
        f"  {r['name'] or r['username']} - {MONTHS[r['month']]} {r['year']}"
        for r in records
    ]
    await update.message.reply_text(
        "*🩸 HALL OF RECORD*\n——————————————\n" + "\n\n".join(lines),
        parse_mode="Markdown"
    )


async def cmd_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_register(update)
    members = get_all_members()

    if not members:
        await update.message.reply_text("No Spartans registered yet.")
        return

    lines = [
        f"🩸 {display_name(m)}  {'@' + m['username'] if m['username'] else '—'}"
        for m in members
    ]
    await update.message.reply_text(
        f"*OUTER AGOGE - {len(members)} SPARTANS*\n——————————————\n" + "\n".join(lines),
        parse_mode="Markdown"
    )


async def cmd_moneyin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auto_register(update)
    user  = update.effective_user
    today = date.today()
    args  = context.args

    if not args:
        await update.message.reply_text("Usage: /moneyin <amount>\nExample: /moneyin 1300")
        return

    if args[0].startswith("@") and is_admin(user.id):
        if len(args) < 2:
            await update.message.reply_text("Usage: /moneyin @username <amount>")
            return
        member = get_member_by_username(args[0])
        if not member:
            await update.message.reply_text(f"{args[0]} not found.")
            return
        try:
            amount = float(args[1].replace("$", "").replace(",", ""))
        except ValueError:
            await update.message.reply_text("Invalid amount.")
            return
        submit_money_in(member["telegram_id"], amount, today.month, today.year)
        await update.message.reply_text(
            f"💰 *${amount:,.0f}* logged for *{display_name(member)}* - {MONTHS[today.month]} {today.year}.",
            parse_mode="Markdown"
        )
        return

    try:
        amount = float(args[0].replace("$", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("Invalid amount. Example: /moneyin 1300")
        return

    submit_money_in(user.id, amount, today.month, today.year)
    name = user.first_name or "Spartan"
    await update.message.reply_text(
        f"💰 *${amount:,.0f}* logged, *{name}* - {MONTHS[today.month]} {today.year}.",
        parse_mode="Markdown"
    )


# ─── ADMIN COMMANDS ────────────────────────────────────────────────────────────

async def cmd_badge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only. 🩸")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /badge @username CONQUEROR|GLADIATOR")
        return

    member = get_member_by_username(context.args[0])
    if not member:
        await update.message.reply_text(f"{context.args[0]} not found.")
        return

    badge_type = context.args[1].upper()
    if badge_type not in VALID_BADGES:
        await update.message.reply_text(f"Badge must be: {', '.join(VALID_BADGES)}")
        return

    today = date.today()
    award_badge(member["telegram_id"], badge_type, today.month, today.year)

    await update.message.reply_text(
        f"🩸 *{BADGE_DISPLAY[badge_type]}*\n\n"
        f"Awarded to *{display_name(member)}*.\n"
        f"Earned. Recorded. Forever in the Hall.",
        parse_mode="Markdown"
    )


async def cmd_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only. 🩸")
        return

    if not context.args:
        active = get_active_challenge()
        if active:
            await update.message.reply_text(
                f"*💪 ACTIVE CHALLENGE:*\n\n{active['description']}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("No active challenge.\nUsage: /challenge <description>")
        return

    description = " ".join(context.args)
    post_challenge(description, update.effective_user.id)

    await update.message.reply_text(
        "💪 *NEW FITNESS CHALLENGE*\n"
        "——————————————\n"
        f"{description}\n"
        "——————————————\n\n"
        "One Spartan claims 🩸 *GLADIATOR*.",
        parse_mode="Markdown"
    )


async def cmd_winner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only. 🩸")
        return

    if not context.args:
        await update.message.reply_text("Usage: /winner @username")
        return

    member = get_member_by_username(context.args[0])
    if not member:
        await update.message.reply_text(f"{context.args[0]} not found.")
        return

    challenge = complete_challenge(member["telegram_id"])
    if not challenge:
        await update.message.reply_text("No active challenge. Post one with /challenge <description>")
        return

    today = date.today()
    award_badge(member["telegram_id"], "GLADIATOR", today.month, today.year)
    name = display_name(member)

    await update.message.reply_text(
        f"🩸 *GLADIATOR - {name.upper()}*\n\n"
        f"_{challenge['description']}_\n\n"
        f"Title held until the next challenge is conquered.",
        parse_mode="Markdown"
    )


async def cmd_removemoneyin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Admin only. 🩸")
        return

    if not context.args:
        await update.message.reply_text("Usage: /removemoneyin @username")
        return

    member = get_member_by_username(context.args[0])
    if not member:
        await update.message.reply_text(f"{context.args[0]} not found.")
        return

    today   = date.today()
    removed = remove_money_in(member["telegram_id"], today.month, today.year)
    name    = display_name(member)

    if removed:
        await update.message.reply_text(f"Entry removed for {name} - {MONTHS[today.month]} {today.year}.")
    else:
        await update.message.reply_text(f"No entry found for {name} this month.")
