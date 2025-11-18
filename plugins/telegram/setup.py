#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Setup flow for Telegram Menu Bot - separate from main notification bot"""

import re
import time
import random
import requests


def setupIkaChef(session):
    """Configure ikaChef (Telegram interactive bot) credentials

    This creates a second bot specifically for menu interaction.
    The main notification bot (session["shared"]["telegram"]) continues
    to handle alerts and captchas without message consumption conflicts.

    Args:
        session: ikabot Session object

    Returns:
        bool: True if setup successful, False otherwise
    """
    print("\n👨‍🍳 ikaChef Setup")
    print("=" * 40)
    print("This is a SEPARATE bot from your notification bot.")
    print("ikaChef handles interactive menu control via Telegram.")
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

    # Generate random 4-digit PIN
    pin = str(random.randint(0, 9999)).zfill(4)

    print()
    print(f"3. Send this command to your bot on Telegram:")
    print(f"   /ikachef {pin}")
    print()
    print("Waiting for command... (Press Ctrl+C to cancel)")

    # Poll for messages with PIN
    start_time = time.time()
    chat_id = None

    try:
        while True:
            elapsed = int(time.time() - start_time)
            print(f"Waiting for /ikachef {pin}... ({elapsed}s)", end="\r")

            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            response = requests.get(url, timeout=10)
            data = response.json()

            if not data.get("ok"):
                time.sleep(2)
                continue

            # Check all messages for PIN
            for update in data.get("result", []):
                if "message" not in update:
                    continue
                if "text" not in update["message"]:
                    continue

                text = update["message"]["text"].strip()
                if text == f"/ikachef {pin}":
                    chat_id = update["message"]["from"]["id"]
                    break

            if chat_id:
                print()
                print(f"✅ Verified! Chat ID: {chat_id}")
                break

            time.sleep(2)

    except KeyboardInterrupt:
        print()
        print(f"❌ Cancelled. Did not receive /ikachef {pin}")
        return False
    except Exception as e:
        print()
        print(f"❌ Error: {e}")
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

        # Send confirmation message
        try:
            from ikabot.helpers.botComm import sendToBot

            # Temporarily set telegram data to menu bot for sending
            temp_data = session.getSessionData()
            original_telegram = temp_data["shared"].get("telegram", {}).copy()

            temp_data["shared"]["telegram"] = {
                "botToken": bot_token,
                "chatId": str(chat_id),
            }
            session.setSessionData(temp_data, shared=True)

            sendToBot(
                session,
                "👨‍🍳 ikaChef configured successfully!\n\n"
                "You can now run: python telegram_bot.py",
                Token=True,
            )

            # Restore original telegram data
            temp_data["shared"]["telegram"] = original_telegram
            session.setSessionData(temp_data, shared=True)

        except Exception:
            pass  # Non-critical if confirmation fails

        print()
        print("✅ ikaChef configured successfully!")
        print("✅ A confirmation message was sent to Telegram")
        print()
        print("You can now run: python telegram_bot.py")

        return True

    except Exception as e:
        print(f"❌ Error saving configuration: {e}")
        return False


def isIkaChefConfigured(session):
    """Check if ikaChef credentials are configured

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
