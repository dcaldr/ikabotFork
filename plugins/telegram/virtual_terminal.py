#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Virtual terminal for Telegram bot - parallel I/O to terminal and Telegram"""

import sys
from queue import Queue, Empty


class MultiplexedInputStream:
    """Reads from merged queue (terminal + Telegram)"""

    def __init__(self, message_queue):
        self.queue = message_queue

    def readline(self):
        """Block until message available from any source"""
        try:
            message = self.queue.get(timeout=300)  # 5 min timeout
            return message + "\n"
        except Empty:
            return "\n"

    def fileno(self):
        """Return fake file descriptor"""
        return 99


class TeeStdout:
    """Writes to terminal AND captures for Telegram

    This allows CLI to work normally while Telegram can view the screen.
    """

    def __init__(self, screen_buffer, output_control, formatter, session):
        """Initialize tee output

        Args:
            screen_buffer: ScreenBuffer instance
            output_control: OutputControl instance
            formatter: ANSIFormatter instance
            session: ikabot Session instance
        """
        self.original_stdout = sys.__stdout__
        self.screen_buffer = screen_buffer
        self.output_control = output_control
        self.formatter = formatter
        self.session = session
        self.telegram_buffer = []

    def write(self, text):
        """Write to both terminal and buffer"""
        if not text:
            return

        # 1. Write to real terminal (CLI works)
        self.original_stdout.write(text)

        # 2. Add to screen buffer (for /view)
        self.screen_buffer.add(text)

        # 3. Queue for Telegram if monitoring
        if self.output_control.should_send_to_telegram():
            self.telegram_buffer.append(text)

    def flush(self):
        """Flush both terminal and Telegram buffers"""
        # Flush terminal
        self.original_stdout.flush()

        # Send to Telegram if monitoring and has content
        if self.telegram_buffer and self.output_control.should_send_to_telegram():
            text = "".join(self.telegram_buffer)
            formatted = self.formatter.convert(text)

            # Send to ikaChef bot
            try:
                from plugins.telegram.ikachef_comm import sendToIkaChef

                sendToIkaChef(self.session, formatted, Token=True)
            except Exception as e:
                # If ikaChef fails, notify user via notification bot (fallback)
                try:
                    from ikabot.helpers.botComm import sendToBot
                    sendToBot(
                        self.session,
                        f"⚠️ ikaChef send failed: {str(e)}\n\nCheck ikaChef bot configuration.",
                        Token=False
                    )
                except Exception:
                    pass  # Both bots failed, nothing we can do

            self.telegram_buffer = []

    def isatty(self):
        """Return original terminal's isatty status"""
        return self.original_stdout.isatty()
