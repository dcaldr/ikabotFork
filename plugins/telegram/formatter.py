#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""ANSI to Telegram format converter"""

import re


class ANSIFormatter:
    """Convert ANSI escape codes to Telegram Markdown and make links clickable"""

    def __init__(self):
        # Patterns for ANSI code conversion
        self.ansi_patterns = [
            # Remove all ANSI escape codes
            (r"\033\[[0-9;]*m", ""),
            # Remove other escape sequences
            (r"\033\[[\d;]*[A-Za-z]", ""),
        ]

        # Patterns for making links clickable
        self.link_patterns = [
            # Full URLs (http/https)
            (r"(https?://[^\s\)]+)", r"[\1](\1)"),
            # IP:port
            (r"\b((?:\d{1,3}\.){3}\d{1,3}:\d+)\b", r"[http://\1](http://\1)"),
            # localhost:port
            (r"\b(localhost:\d+)\b", r"[http://\1](http://\1)"),
            # domain:port (e.g., example.com:8080)
            (r"\b([a-zA-Z0-9.-]+\.[a-zA-Z]{2,}:\d+)\b", r"[http://\1](http://\1)"),
        ]

    def convert(self, text):
        """Convert ANSI codes and make links clickable

        Args:
            text: String with ANSI codes and potential links

        Returns:
            String with ANSI codes removed and links made clickable
        """
        result = text

        # 1. Remove ANSI codes
        for pattern, replacement in self.ansi_patterns:
            result = re.sub(pattern, replacement, result)

        # 2. Make links clickable
        for pattern, replacement in self.link_patterns:
            result = re.sub(pattern, replacement, result)

        return result
