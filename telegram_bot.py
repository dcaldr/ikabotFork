#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot Entry Point for Ikabot

This script runs ikabot through Telegram instead of CLI.
It hijacks stdin/stdout to make the existing menu system work via Telegram messages.

Usage:
    python telegram_bot.py

Requirements:
    - Must have valid Telegram credentials configured (use ikabot CLI first)
    - Must be logged into an Ikariam account
"""

import sys
import time
import signal

from ikabot.web.session import Session
from ikabot.helpers.botComm import telegramDataIsValid
from plugins.telegram.bot import TelegramBot


def main():
    """Main entry point"""
    print("🤖 Ikabot Telegram Bot")
    print("=" * 40)

    # Create session
    print("Loading session...")
    session = Session()

    # Check if logged in
    if not session.logged:
        print("❌ Error: Not logged into Ikariam")
        print("Please run 'ikabot' first and log in")
        return 1

    # Check if Telegram is configured
    if not telegramDataIsValid(session):
        print("❌ Error: Telegram not configured")
        print("Please run 'ikabot' and configure Telegram in Options menu (21 -> 2)")
        return 1

    print("✅ Session loaded")
    print("✅ Telegram configured")
    print()

    # Create bot
    bot = TelegramBot(session)

    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        print("\n👋 Shutting down...")
        bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start bot
    print("🚀 Starting Telegram bot...")
    bot.start()

    print("✅ Bot is running!")
    print("💬 Open Telegram and start chatting with your bot")
    print("Press Ctrl+C to stop")
    print()

    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        bot.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
