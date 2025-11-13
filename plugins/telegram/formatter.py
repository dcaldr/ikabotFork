#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""ANSI to Telegram format converter"""

import re


class ANSIFormatter:
    """Convert ANSI escape codes to Telegram Markdown"""

    def __init__(self):
        # Patterns for ANSI code conversion
        self.patterns = [
            # Remove all ANSI escape codes (simplest approach for now)
            (r'\033\[[0-9;]*m', ''),
            # Remove other escape sequences
            (r'\033\[[\d;]*[A-Za-z]', ''),
        ]

    def convert(self, text):
        """Convert ANSI codes to Telegram-friendly format

        Args:
            text: String with ANSI codes

        Returns:
            String with ANSI codes removed/converted
        """
        result = text

        # Apply all patterns
        for pattern, replacement in self.patterns:
            result = re.sub(pattern, replacement, result)

        # Escape Telegram markdown special characters if needed
        # (keeping it simple for now - just remove ANSI codes)

        return result
