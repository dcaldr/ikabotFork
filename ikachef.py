#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smart launcher for ikabot with ikaChef auto-detection

This wrapper automatically detects if ikaChef is configured and launches
the appropriate mode:
- If ikaChef configured → Run in Telegram interactive mode
- If not configured → Run normal ikabot CLI mode

Usage:
    python ikachef.py                # Auto-detect mode
    python ikachef.py --chef         # Force ikaChef mode (with setup if needed)
    python ikachef.py --cli          # Force normal CLI mode
    python ikachef.py --reconfigure  # Reconfigure ikaChef bot credentials

Maintains zero coupling with core ikabot files.
"""

import sys
import os


def main():
    """Smart launcher with auto-detection"""

    # Parse command line arguments
    force_chef = "--chef" in sys.argv
    force_cli = "--cli" in sys.argv
    force_reconfigure = "--reconfigure" in sys.argv

    # Remove our custom args before passing to ikabot (keep --reconfigure for telegram_bot)
    sys.argv = [arg for arg in sys.argv if arg not in ["--chef", "--cli"]]

    # Force modes if requested
    if force_cli:
        print("🎮 Launching ikabot in CLI mode (forced)")
        from ikabot.command_line import main as ikabot_main
        ikabot_main()
        return

    if force_reconfigure or force_chef:
        if force_reconfigure:
            print("👨‍🍳 Launching ikaChef mode (reconfigure)")
        else:
            print("👨‍🍳 Launching ikaChef mode (forced)")
        try:
            from telegram_bot import main as ikachef_main
            ikachef_main()
        except FileNotFoundError:
            print()
            print("❌ Session file not found (.ikabot)")
            print()
            print("You need to login to ikabot first:")
            print("  1. Run: python -m ikabot")
            print("  2. Login to your Ikariam account")
            print("  3. Exit (select 0)")
            print("  4. Then run: python ikachef.py --chef")
            print()
            return
        return

    # Auto-detection mode
    try:
        from ikabot.web.session import Session
        from ikabot.command_line import init as ikabot_init
        from plugins.telegram.setup import isIkaChefConfigured

        # Initialize ikabot (changes to HOME directory where .ikabot lives)
        ikabot_init()

        # Create session to check configuration
        session = Session()

        # Check if both logged in AND ikaChef configured
        if session.logged and isIkaChefConfigured(session):
            print("👨‍🍳 ikaChef detected - launching Telegram interactive mode")
            print("   (Use 'python ikachef.py --cli' to force CLI mode)")
            print()

            from telegram_bot import main as ikachef_main
            ikachef_main()
        else:
            # Not configured or not logged in
            if not session.logged:
                print("🎮 Not logged in - launching normal ikabot")
            else:
                print("🎮 ikaChef not configured - launching normal ikabot")
                print("   (Configure ikaChef: python ikachef.py --chef)")
            print()

            from ikabot.command_line import main as ikabot_main
            ikabot_main()

    except FileNotFoundError:
        # Session file doesn't exist yet - first time user
        print("🎮 First time setup - launching normal ikabot")
        print("   (Login first, then configure ikaChef)")
        print()
        from ikabot.command_line import main as ikabot_main
        ikabot_main()

    except ImportError:
        # Plugin not available, fall back to normal mode
        print("🎮 ikaChef plugin not found - launching normal ikabot")
        print()
        from ikabot.command_line import main as ikabot_main
        ikabot_main()

    except Exception as e:
        # Any other error, fall back gracefully
        print(f"⚠️  Error during auto-detection: {e}")
        print("🎮 Falling back to normal ikabot mode")
        print()
        from ikabot.command_line import main as ikabot_main
        ikabot_main()


if __name__ == "__main__":
    main()
