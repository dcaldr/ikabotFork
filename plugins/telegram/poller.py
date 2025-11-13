#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Telegram message poller"""

import threading
import time
from requests import get


class TelegramPoller:
    """Polls Telegram Bot API for updates"""

    def __init__(self, bot_token, chat_id, handler):
        """Initialize poller

        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID to filter messages
            handler: Callback function(update) to handle messages
        """
        self.bot_token = bot_token
        self.chat_id = int(chat_id)
        self.handler = handler
        self.last_update_id = 0
        self.running = False
        self.thread = None

    def start(self):
        """Start polling in background thread"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop polling"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _poll_loop(self):
        """Long polling loop - runs in background thread"""
        while self.running:
            try:
                # Long polling with 30s timeout
                response = get(
                    f"https://api.telegram.org/bot{self.bot_token}/getUpdates",
                    params={
                        "offset": self.last_update_id + 1,
                        "timeout": 30
                    },
                    timeout=35  # Slightly longer than API timeout
                ).json()

                # Process updates
                for update in response.get("result", []):
                    self.last_update_id = update["update_id"]

                    # Filter by chat_id and only process messages
                    if "message" in update:
                        msg = update["message"]
                        if msg.get("chat", {}).get("id") == self.chat_id:
                            # Call handler with the update
                            try:
                                self.handler(update)
                            except Exception:
                                pass  # Silently ignore handler errors

            except Exception:
                # On any error, wait and retry
                time.sleep(5)
