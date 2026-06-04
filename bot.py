#!/usr/bin/env python3
"""
OUTER AGOGE — Telegram Bot v2
Smart channel tracking. No commands needed for daily rituals. ⚔️
"""

import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from database import init_db
from channel_tracker import handle_message
from handlers import (
    cmd_setup, cmd_help,
    cmd_leaderboard, cmd_streak, cmd_mystats, cmd_hall, cmd_members,
    cmd_badge, cmd_challenge, cmd_winner, cmd_removemoneyin, cmd_moneyin
)

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN not set.")

    init_db()
    logger.info("Database initialized ✓")

    app = Application.builder().token(token).build()

    # ── Smart message tracker (runs on every group message)
    app.add_handler(MessageHandler(filters.Chat(chat_type=["group", "supergroup"]), handle_message))

    # ── Viewing commands (available to all members)
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("lb",          cmd_leaderboard))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("streak",      cmd_streak))
    app.add_handler(CommandHandler("mystats",     cmd_mystats))
    app.add_handler(CommandHandler("hall",        cmd_hall))
    app.add_handler(CommandHandler("members",     cmd_members))
    app.add_handler(CommandHandler("moneyin",     cmd_moneyin))   # manual override

    # ── Admin commands
    app.add_handler(CommandHandler("setup",         cmd_setup))
    app.add_handler(CommandHandler("badge",         cmd_badge))
    app.add_handler(CommandHandler("challenge",     cmd_challenge))
    app.add_handler(CommandHandler("winner",        cmd_winner))
    app.add_handler(CommandHandler("removemoneyin", cmd_removemoneyin))

    logger.info("⚔️  OUTER AGOGE Bot is live — monitoring channels.")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
