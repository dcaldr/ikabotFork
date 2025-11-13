#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Output control for Telegram bot - manages quiet/monitor modes"""

import threading


class OutputControl:
    """Controls whether output is sent to Telegram

    Modes:
        - quiet: Output captured but not sent to Telegram
        - monitor: Output sent to Telegram in real-time

    Always starts in quiet mode. First non-command message enables monitor.
    """

    def __init__(self):
        """Initialize in quiet mode"""
        self.mode = "quiet"
        self.first_message_received = False
        self.lock = threading.Lock()

    def set_quiet(self):
        """Disable sending output to Telegram"""
        with self.lock:
            self.mode = "quiet"

    def set_monitor(self):
        """Enable sending output to Telegram"""
        with self.lock:
            self.mode = "monitor"

    def should_send_to_telegram(self):
        """Check if output should be sent to Telegram

        Returns:
            bool: True if in monitor mode
        """
        with self.lock:
            return self.mode == "monitor"

    def on_first_message(self):
        """Handle first non-command message

        Automatically enables monitor mode on first message.

        Returns:
            bool: True if this was the first message (mode changed)
        """
        with self.lock:
            if not self.first_message_received:
                self.first_message_received = True
                self.mode = "monitor"
                return True
            return False

    def get_mode(self):
        """Get current mode

        Returns:
            str: Current mode ("quiet" or "monitor")
        """
        with self.lock:
            return self.mode
