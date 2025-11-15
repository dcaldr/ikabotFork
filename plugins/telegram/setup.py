#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Setup flow for Telegram Menu Bot - separate from main notification bot"""

import re
import requests


def updateTelegramMenuBotData(session):
    """Configure Telegram Menu Bot credentials (separate from alert bot)

    This creates a second bot specifically for menu interaction.
    The main notification bot (session["shared"]["telegram"]) continues
    to handle alerts and captchas without message consumption conflicts.

    Args:
        session: ikabot Session object

    Returns:
        bool: True if setup successful, False otherwise
    """
    print("\n🤖 Telegram Menu Bot Setup")
    print("=" * 40)
    print("This is a SEPARATE bot from your notification bot.")
    print("It will handle menu interactions via Telegram.")
    print()

    # Get bot token
    print("1. Create a new bot with @BotFather on Telegram")
    print("2. Copy the bot token")
    print()
    bot_token = input("Enter bot token: ").strip()

    if not bot_token:
        print("❌ No token provided")
        return False

    # Validate token format
    if not re.match(r"^\d+:[A-Za-z0-9_-]+$", bot_token):
        print("❌ Invalid token format")
        return False

    # Get bot info to verify token
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        data = response.json()

        if not data.get("ok"):
            print("❌ Invalid bot token")
            return False

        bot_name = data["result"]["username"]
        print(f"✅ Connected to bot: @{bot_name}")
    except Exception as e:
        print(f"❌ Error verifying token: {e}")
        return False

    # Get chat ID
    print()
    print("3. Send /start to your bot on Telegram")
    print("4. Press Enter when done")
    input()

    # Poll for messages
    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)
        data = response.json()

        if not data.get("ok"):
            print("❌ Error getting updates")
            return False

        updates = data.get("result", [])
        if not updates:
            print("❌ No messages received. Please send /start to the bot")
            return False

        # Get chat ID from latest message
        chat_id = updates[-1]["message"]["chat"]["id"]
        print(f"✅ Chat ID: {chat_id}")

    except Exception as e:
        print(f"❌ Error getting chat ID: {e}")
        return False

    # Save to session
    try:
        session_data = session.getSessionData()

        if "shared" not in session_data:
            session_data["shared"] = {}

        if "telegramMenu" not in session_data["shared"]:
            session_data["shared"]["telegramMenu"] = {}

        session_data["shared"]["telegramMenu"]["botToken"] = bot_token
        session_data["shared"]["telegramMenu"]["chatId"] = str(chat_id)

        session.setSessionData(session_data, shared=True)

        print()
        print("✅ Menu bot configured successfully!")
        print()
        print("You can now run: python telegram_bot.py")

        return True

    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False


def telegramMenuBotDataIsValid(session):
    """Check if menu bot credentials are configured

    Args:
        session: ikabot Session object

    Returns:
        bool: True if valid credentials exist
    """
    try:
        session_data = session.getSessionData()

        if "shared" not in session_data:
            return False

        if "telegramMenu" not in session_data["shared"]:
            return False

        telegram_menu = session_data["shared"]["telegramMenu"]

        if "botToken" not in telegram_menu or "chatId" not in telegram_menu:
            return False

        bot_token = telegram_menu["botToken"]
        chat_id = telegram_menu["chatId"]

        if not bot_token or not chat_id:
            return False

        return True

    except Exception:
        return False
