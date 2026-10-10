#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram Bot Entry Point for Ikabot - Parallel Mode

This script runs alongside CLI - both work simultaneously.
Terminal output is captured and can be viewed via Telegram.
Input can come from either terminal or Telegram.

Usage:
    python telegram_bot.py                # Run ikaChef bot
    python telegram_bot.py --reconfigure  # Reconfigure bot credentials
    python telegram_bot.py --delete       # Delete ikaChef credentials

Requirements:
    - Must have valid Telegram credentials (use ikabot CLI first: menu 21 -> 2)
    - Must be logged into an Ikariam account
"""

import sys
import signal

from ikabot.web.session import Session
from ikabot.command_line import menu, init
from plugins.telegram.bot import TelegramBot
from plugins.telegram.screen_buffer import ScreenBuffer
from plugins.telegram.virtual_terminal import MultiplexedInputStream, TeeStdout
from plugins.telegram.formatter import ANSIFormatter
from plugins.telegram.output_control import OutputControl
from plugins.telegram.setup import isIkaChefConfigured, setupIkaChef, deleteIkaChef


def setup_clear_detection(screen_buffer):
    """Monkey-patch clear() to detect screen wipes

    This allows us to reset the buffer when the screen is cleared,
    so /view shows only content since last clear.

    Args:
        screen_buffer: ScreenBuffer instance to notify on clear
    """
    import ikabot.helpers.gui as gui

    # Save original
    original_clear = gui.clear

    # Create wrapper
    def clear_with_detection():
        """Call original clear() and notify buffer"""
        original_clear()
        screen_buffer.mark_cleared()

    # Replace
    gui.clear = clear_with_detection


def main():
    """Main entry point"""
    print("👨‍🍳 ikaChef - Interactive Menu via Telegram")
    print("=" * 40)

    # Parse command-line arguments
    force_reconfigure = "--reconfigure" in sys.argv
    force_delete = "--delete" in sys.argv

    # Initialize ikabot (changes to HOME directory where .ikabot lives)
    init()

    # Create session
    print("Loading session...")
    session = Session()

    # Check if logged in
    if not session.logged:
        print("❌ Error: Not logged into Ikariam")
        print("Please run 'ikabot' first and log in")
        return 1

    # Handle delete request
    if force_delete:
        print("🗑️  Deleting ikaChef credentials...")
        print()
        if deleteIkaChef(session):
            print()
            print("ikaChef has been removed from your session.")
            print("You can reconfigure it anytime with: python ikachef.py --chef")
            return 0
        else:
            return 1

    # Check if ikaChef is configured
    is_configured = isIkaChefConfigured(session)

    # Handle reconfigure request
    if force_reconfigure and is_configured:
        print("🔄 Reconfiguring ikaChef...")
        print()
        if not setupIkaChef(session):
            print("Setup failed. Please try again.")
            return 1
    elif not is_configured:
        print("❌ ikaChef not configured")
        print()
        print("ikaChef is SEPARATE from your notification bot.")
        print("It handles interactive menu control without interfering with alerts/captchas.")
        print()

        response = input("Configure now? (y/n): ").strip().lower()
        if response != "y":
            print("Setup cancelled. Run again when ready.")
            return 1

        if not setupIkaChef(session):
            print("Setup failed. Please try again.")
            return 1

    print("✅ Session loaded")
    print("✅ ikaChef configured")
    print()

    # Create shared components
    screen_buffer = ScreenBuffer()
    output_control = OutputControl()
    formatter = ANSIFormatter()

    # Setup clear() detection
    setup_clear_detection(screen_buffer)

    # Create bot (will start polling)
    bot = TelegramBot(session, screen_buffer)
    bot.output_control = output_control  # Share output control

    # Hijack stdout with tee
    tee_stdout = TeeStdout(screen_buffer, output_control, formatter, session)
    sys.stdout = tee_stdout

    # Hijack stdin with multiplexed input
    multiplexed_stdin = MultiplexedInputStream(bot.message_queue)
    sys.stdin = multiplexed_stdin

    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        print("\n👋 Shutting down...")
        # Restore original streams
        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
        bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start bot (begins polling)
    print("🚀 Starting ikaChef...")
    bot.start()

    print("✅ ikaChef is running in parallel mode!")
    print("✅ Terminal works normally (CLI)")
    print("✅ Telegram can view/interact via commands")
    print()
    print("Press Ctrl+C to stop")
    print()

    # Run menu in main thread
    try:
        while bot.running:
            menu(session, checkUpdate=False)
    except KeyboardInterrupt:
        pass
    finally:
        # Restore original streams
        sys.stdout = sys.__stdout__
        sys.stdin = sys.__stdin__
        bot.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
