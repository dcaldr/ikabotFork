#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""Screen buffer for Telegram bot - captures output between clear() calls"""


class ScreenBuffer:
    """Circular buffer that resets on clear() calls

    Stores all output between clear() calls (unlimited), then resets.
    Handles Telegram's 4096 character message limit by splitting.
    """

    def __init__(self):
        """Initialize empty buffer"""
        self.lines = []
        self.on_clear_callback = None

    def mark_cleared(self):
        """Called when terminal screen is cleared

        Resets buffer to empty state and triggers callback if set.
        """
        self.lines = []
        if self.on_clear_callback:
            self.on_clear_callback()

    def add(self, text):
        """Add text to buffer

        Args:
            text: Text to add (can contain newlines)
        """
        if not text:
            return

        # Split by newlines and store each line
        for line in text.split("\n"):
            # Keep empty lines to preserve formatting
            self.lines.append(line)

    def get_screen(self):
        """Get current screen content (since last clear)

        Returns:
            list: List of message chunks (each <= 4000 chars for Telegram)
        """
        # Join all lines
        text = "\n".join(self.lines)

        # If empty, return single empty message
        if not text.strip():
            return ["(Screen is empty)"]

        # Split into chunks if needed (Telegram limit: 4096 chars)
        # Use 4000 to leave room for formatting
        max_chunk_size = 4000

        if len(text) <= max_chunk_size:
            return [text]

        # Split into chunks, trying to break at newlines
        chunks = []
        current_chunk = []
        current_length = 0

        for line in self.lines:
            line_length = len(line) + 1  # +1 for newline

            if current_length + line_length > max_chunk_size:
                # Current chunk is full, start new one
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_length = line_length
                else:
                    # Single line is too long, split it
                    chunks.append(line[:max_chunk_size])
                    current_chunk = [line[max_chunk_size:]]
                    current_length = len(current_chunk[0])
            else:
                current_chunk.append(line)
                current_length += line_length

        # Add final chunk
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks if chunks else ["(Screen is empty)"]
