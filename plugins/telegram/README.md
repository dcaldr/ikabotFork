# Telegram Plugin for Ikabot

This plugin enables running ikabot through Telegram instead of the CLI.

## Architecture

The plugin uses a **virtual terminal emulator** that:
1. Hijacks `sys.stdin` to read from a Telegram message queue
2. Hijacks `sys.stdout` to send output to Telegram
3. Runs the existing `command_line.menu()` unchanged
4. All core functions work automatically without modification

## Files

- `virtual_terminal.py` - stdin/stdout hijacking (~100 lines)
- `bot.py` - Main coordinator (~110 lines)
- `poller.py` - Telegram polling (~80 lines)
- `formatter.py` - ANSI → Telegram conversion (~40 lines)

## Usage

1. First, configure Telegram credentials using the CLI:
   ```bash
   python ikabot
   # Go to Options (21) -> Enter Telegram data (2)
   ```

2. Run the Telegram bot:
   ```bash
   python telegram_bot.py
   ```

3. Open Telegram and chat with your bot. The ikabot menu will appear.

4. Type menu option numbers to interact (e.g., "17" for Auto-Pirate).

## Key Features

- ✅ Zero changes to core ikabot files
- ✅ New functions added to ikabot work automatically
- ✅ ANSI colors are stripped for Telegram compatibility
- ✅ Works alongside CLI (not simultaneously, but alternating)
- ✅ No new dependencies

## How It Works

```
User Message (Telegram)
    ↓
TelegramPoller receives update
    ↓
Message added to Queue
    ↓
TelegramInputStream.readline() returns message
    ↓
ikabot menu thinks it got CLI input
    ↓
ikabot prints output
    ↓
TelegramOutputStream captures output
    ↓
ANSIFormatter strips colors
    ↓
sendToBot() sends to Telegram
```

## Technical Details

### Virtual Terminal

The `virtual_terminal.py` module provides context manager that:
- Saves original stdin/stdout
- Replaces with Telegram versions
- Restores originals on exit

### Message Flow

1. **Input**: Telegram messages → Queue → fake stdin → `input()`
2. **Output**: `print()` → fake stdout → format → `sendToBot()`

### Threading Model

- Main thread: Keeps process alive
- Poller thread: Long-polls Telegram API
- Menu thread: Runs ikabot menu with hijacked I/O

## Limitations

- Cannot run CLI and Telegram simultaneously (they share the same session)
- Long-running tasks may timeout the Telegram session
- Binary/image output not supported (text only)

## Zero-Coupling Design

This plugin achieves complete decoupling from core:
- Only imports: `command_line.menu()`, `Session`, `sendToBot()`
- No function registry or metadata needed
- No modifications to existing functions
- No awareness of function implementations
