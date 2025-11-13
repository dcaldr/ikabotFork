#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Main Telegram bot coordinator"""

import threading
from queue import Queue

from ikabot.command_line import menu
from ikabot.helpers.botComm import sendToBot
from plugins.telegram.virtual_terminal import virtual_terminal
from plugins.telegram.formatter import ANSIFormatter
from plugins.telegram.poller import TelegramPoller


class TelegramBot:
    """Main bot - runs ikabot menu via Telegram"""

    def __init__(self, session):
        """Initialize bot

        Args:
            session: ikabot Session object
        """
        self.session = session
        self.message_queue = Queue()
        self.formatter = ANSIFormatter()
        self.running = False

        # Get bot credentials from session
        session_data = session.getSessionData()
        telegram_data = session_data["shared"]["telegram"]
        bot_token = telegram_data["botToken"]
        chat_id = telegram_data["chatId"]

        # Create poller
        self.poller = TelegramPoller(bot_token, chat_id, self._handle_message)

        # Menu thread
        self.menu_thread = None

    def start(self):
        """Start bot - begins polling and menu loop"""
        if self.running:
            return

        self.running = True

        # Start polling for messages
        self.poller.start()

        # Send welcome message
        try:
            sendToBot(
                self.session,
                "🤖 Ikabot Telegram Interface Ready!\n\n"
                "The menu will appear below. Type menu option numbers to interact.",
                Token=True
            )
        except Exception:
            pass

        # Run menu loop in thread
        self.menu_thread = threading.Thread(target=self._run_menu, daemon=True)
        self.menu_thread.start()

    def stop(self):
        """Stop bot"""
        self.running = False
        self.poller.stop()

        # Send goodbye message
        try:
            sendToBot(self.session, "👋 Telegram interface stopped.", Token=True)
        except Exception:
            pass

    def _handle_message(self, update):
        """Handle incoming Telegram message

        Args:
            update: Telegram update dict
        """
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"].strip()

            # Skip empty messages and bot commands like /start
            if not text or text.startswith("/"):
                return

            # Add message to queue for menu to consume
            self.message_queue.put(text)

    def _run_menu(self):
        """Run menu() with hijacked stdin/stdout - runs in background thread"""
        while self.running:
            try:
                # Run menu with virtual terminal
                with virtual_terminal(self.session, self.formatter, self.message_queue):
                    # This blocks and runs the interactive menu
                    # It thinks it's in CLI but actually reads from Telegram
                    menu(self.session, checkUpdate=False)
            except Exception:
                # If menu exits or crashes, restart it
                if self.running:
                    import time
                    time.sleep(2)
                    continue
                else:
                    break
