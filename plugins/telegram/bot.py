#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Main Telegram bot coordinator - parallel CLI and Telegram interface"""

import sys
import threading
from queue import Queue

from ikabot.command_line import menu
from ikabot.helpers.botComm import sendToBot
from plugins.telegram.virtual_terminal import MultiplexedInputStream, TeeStdout
from plugins.telegram.formatter import ANSIFormatter
from plugins.telegram.poller import TelegramPoller
from plugins.telegram.screen_buffer import ScreenBuffer
from plugins.telegram.output_control import OutputControl

# ===== COMMAND CONFIGURATION =====
# Change command names here
COMMANDS = {
    "view": "view",  # Show current screen
    "monitor": "monitor",  # Enable output to Telegram
    "mute": "mute",  # Disable output to Telegram
    "stop": "stop",  # Shutdown bot
    "help": "help",  # Show help
}
# ==================================


class TelegramBot:
    """Main bot - runs parallel to CLI, both work simultaneously"""

    def __init__(self, session, screen_buffer):
        """Initialize bot

        Args:
            session: ikabot Session object
            screen_buffer: ScreenBuffer instance (shared with main)
        """
        self.session = session
        self.message_queue = Queue()
        self.formatter = ANSIFormatter()
        self.screen_buffer = screen_buffer
        self.output_control = OutputControl()
        self.running = False

        # Get menu bot credentials from session (separate from notification bot)
        session_data = session.getSessionData()
        telegram_menu_data = session_data["shared"]["telegramMenu"]
        bot_token = telegram_menu_data["botToken"]
        chat_id = telegram_menu_data["chatId"]

        # Create poller
        self.poller = TelegramPoller(bot_token, chat_id, self._handle_message)

    def start(self):
        """Start bot - begins polling"""
        if self.running:
            return

        self.running = True

        # Start polling for messages
        self.poller.start()

        # Send welcome message
        try:
            sendToBot(
                self.session,
                "🤖 Telegram Bot Started (Quiet Mode)\n\n"
                f"Use /{COMMANDS['view']} to see current screen\n"
                f"Send any message to interact",
                Token=True,
            )
        except Exception:
            pass

    def stop(self, kill_tasks=False):
        """Stop bot

        Args:
            kill_tasks: If True, also kill all ikabot background tasks
        """
        self.running = False
        self.poller.stop()

        if kill_tasks:
            # Kill all ikabot tasks
            try:
                import os
                import signal
                from ikabot.helpers.process import updateProcessList

                process_list = updateProcessList(self.session)
                for proc in process_list:
                    try:
                        os.kill(proc["pid"], signal.SIGTERM)
                    except Exception:
                        pass

                sendToBot(
                    self.session,
                    f"🛑 Stopped bot and killed {len(process_list)} tasks",
                    Token=True,
                )
            except Exception:
                sendToBot(self.session, "🛑 Bot stopped", Token=True)
        else:
            try:
                sendToBot(self.session, "🛑 Bot stopped", Token=True)
            except Exception:
                pass

    def _handle_message(self, update):
        """Handle incoming Telegram message

        Args:
            update: Telegram update dict
        """
        if "message" not in update or "text" not in update["message"]:
            return

        text = update["message"]["text"].strip()

        if not text:
            return

        # Handle commands
        if text.startswith("/"):
            self._handle_command(text)
            return

        # First non-command message → auto-enable monitoring
        if self.output_control.on_first_message():
            try:
                sendToBot(self.session, "📢 Monitoring started", Token=True)
            except Exception:
                pass

        # Add message to stdin queue
        self.message_queue.put(text)

    def _handle_command(self, command):
        """Handle bot commands

        Args:
            command: Command string starting with /
        """
        cmd = command.lower()

        # /view - Show current screen
        if cmd == f"/{COMMANDS['view']}":
            chunks = self.screen_buffer.get_screen()
            for chunk in chunks:
                try:
                    sendToBot(self.session, chunk, Token=True)
                except Exception:
                    pass

        # /monitor - Enable output
        elif cmd == f"/{COMMANDS['monitor']}":
            self.output_control.set_monitor()
            try:
                sendToBot(self.session, "📢 Monitoring started", Token=True)
            except Exception:
                pass

        # /mute - Disable output
        elif cmd == f"/{COMMANDS['mute']}":
            self.output_control.set_quiet()
            try:
                sendToBot(self.session, "🔇 Muted", Token=True)
            except Exception:
                pass

        # /stop - Shutdown with options
        elif cmd.startswith(f"/{COMMANDS['stop']}"):
            parts = cmd.split()

            if len(parts) == 1:
                # Just /stop - ask for confirmation
                try:
                    sendToBot(
                        self.session,
                        "Stop telegram bot?\n\n"
                        f"/{COMMANDS['stop']} bot - Stop bot only\n"
                        f"/{COMMANDS['stop']} all - Stop bot + kill tasks",
                        Token=True,
                    )
                except Exception:
                    pass

            elif len(parts) == 2:
                if parts[1] == "bot":
                    self.stop(kill_tasks=False)
                elif parts[1] == "all":
                    self.stop(kill_tasks=True)

        # /help - Show help
        elif cmd == f"/{COMMANDS['help']}":
            help_text = (
                "🤖 Telegram Bot Commands\n\n"
                f"/{COMMANDS['view']} - Show current screen\n"
                f"/{COMMANDS['monitor']} - Enable output\n"
                f"/{COMMANDS['mute']} - Disable output\n"
                f"/{COMMANDS['stop']} - Stop bot\n"
                f"/{COMMANDS['help']} - Show this help\n\n"
                "Send any number to interact with menu"
            )
            try:
                sendToBot(self.session, help_text, Token=True)
            except Exception:
                pass
