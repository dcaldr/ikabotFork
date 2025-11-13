#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Virtual terminal for Telegram bot - hijacks stdin/stdout"""

import sys
from contextlib import contextmanager
from queue import Queue, Empty
from ikabot.helpers.botComm import sendToBot


class TelegramInputStream:
    """Fake stdin that reads from Telegram message queue"""

    def __init__(self, message_queue):
        self.queue = message_queue

    def readline(self):
        """Block until message available, return with newline"""
        try:
            message = self.queue.get(timeout=300)  # 5 min timeout
            return message + "\n"
        except Empty:
            return "\n"  # Return empty line on timeout

    def fileno(self):
        """Return fake file descriptor"""
        return 99


class TelegramOutputStream:
    """Fake stdout that sends to Telegram"""

    def __init__(self, session, formatter):
        self.session = session
        self.formatter = formatter
        self.buffer = []

    def write(self, text):
        """Buffer text, send complete messages"""
        if not text or text == '\n':
            return

        # Split on newlines and add to buffer
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line:  # Skip empty lines
                self.buffer.append(line)
            # If not the last element or last element is empty (ends with \n), flush
            if i < len(lines) - 1 or (i == len(lines) - 1 and not lines[-1]):
                self.flush()

    def flush(self):
        """Send buffered output to Telegram"""
        if self.buffer:
            # Join buffer and convert ANSI codes
            message = "\n".join(self.buffer)
            formatted = self.formatter.convert(message)

            # Send to Telegram
            try:
                sendToBot(self.session, formatted, Token=True)
            except Exception:
                pass  # Silently ignore send errors

            # Clear buffer
            self.buffer = []

    def isatty(self):
        """Return False to indicate non-interactive terminal"""
        return False


@contextmanager
def virtual_terminal(session, formatter, message_queue):
    """Context manager for stdin/stdout hijacking

    Usage:
        with virtual_terminal(session, formatter, queue):
            # Code here will read from queue and write to Telegram
            menu(session)
    """
    # Save originals
    original_stdin = sys.stdin
    original_stdout = sys.stdout

    # Create Telegram versions
    telegram_stdin = TelegramInputStream(message_queue)
    telegram_stdout = TelegramOutputStream(session, formatter)

    try:
        # Hijack stdin/stdout
        sys.stdin = telegram_stdin
        sys.stdout = telegram_stdout

        yield

    finally:
        # Restore originals
        sys.stdout = original_stdout
        sys.stdin = original_stdin
