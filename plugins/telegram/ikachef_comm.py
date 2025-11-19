#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Communication helpers for ikaChef bot - separate from notification bot"""

from requests import get


def sendToIkaChef(session, msg, Token=False):
    """Send message to ikaChef bot (not notification bot)

    This function sends directly to the ikaChef bot without touching
    the notification bot credentials in session["shared"]["telegram"].

    Args:
        session: ikabot Session object
        msg: Message text to send
        Token: If False, adds pid/server/world/player info to message

    Returns:
        requests.Response or None
    """
    # Get ikaChef credentials from session
    session_data = session.getSessionData()

    if "shared" not in session_data or "ikaChef" not in session_data["shared"]:
        return None

    ikachef_data = session_data["shared"]["ikaChef"]
    bot_token = ikachef_data.get("botToken")
    chat_id = ikachef_data.get("chatId")

    if not bot_token or not chat_id:
        return None

    # Add context info if requested
    if Token is False:
        import os
        infoUser = "Server:{}, World:{}, Player:{}".format(
            session.servidor, session.word, session.username
        )
        msg = "pid:{}\n{}\n{}".format(os.getpid(), infoUser, msg)

    # Send directly to ikaChef bot
    try:
        return get(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            params={"chat_id": chat_id, "text": msg},
        )
    except Exception:
        return None
