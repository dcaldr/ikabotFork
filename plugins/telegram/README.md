# Telegram Plugin for Ikabot - Parallel Mode

This plugin enables viewing and interacting with ikabot via Telegram while the terminal continues to work normally.

## Architecture

The plugin uses a **parallel I/O model** that:
1. Tees `sys.stdout` to both terminal AND buffer (CLI works normally)
2. Multiplexes `sys.stdin` from both terminal AND Telegram
3. Detects screen clears via monkey-patched `clear()` function
4. Provides Telegram commands to view screen and control output

## Key Features

- ✅ **Parallel operation**: Terminal and Telegram work simultaneously
- ✅ **Zero core changes**: Only new files in `plugins/` directory
- ✅ **Screen buffer**: View exactly what's on screen since last `clear()`
- ✅ **Auto-monitor**: First message enables output to Telegram
- ✅ **Clickable links**: HTTP URLs, IP:port, localhost automatically linked
- ✅ **No new dependencies**: Uses only standard library + existing requests

## Files

- `virtual_terminal.py` - Tee stdout, multiplexed stdin (~90 lines)
- `bot.py` - Main coordinator with commands (~210 lines)
- `poller.py` - Telegram polling (~80 lines)
- `formatter.py` - ANSI removal + link detection (~50 lines)
- `screen_buffer.py` - Circular buffer with clear detection (~90 lines)
- `output_control.py` - Quiet/monitor mode management (~70 lines)

**Total: ~590 lines**

## Usage

### 1. Configure Telegram (one-time setup)

```bash
python ikabot
# Go to Options (21) -> Enter Telegram data (2)
```

### 2. Run Telegram Bot

```bash
python telegram_bot.py
```

Terminal continues to work normally. Telegram bot runs in parallel.

### 3. Telegram Commands

```
/view       - Show current screen (since last clear)
/monitor    - Enable output to Telegram
/mute       - Disable output to Telegram
/stop       - Shutdown bot (asks bot/all)
/help       - Show available commands
```

### 4. Interact

Send any message (not starting with `/`) to interact with menu:

```
You: /view
Bot: (shows menu)

You: 17                    ← First message
Bot: 📢 Monitoring started
     ⚠️ WARNING ⚠️
     How many missions?

You: 5
Bot: Do you want to schedule?

You: /mute                 ← Stop spam
Bot: 🔇 Muted

You: n
You: 3
     [Telegram stays quiet]

You: /view
Bot: ✅ Task started!
     (shows current menu)
```

## How It Works

### Input Flow

```
Terminal Keyboard           Telegram Messages
        ↓                          ↓
        └────→ Merged Queue ←──────┘
                    ↓
         MultiplexedInputStream
                    ↓
              input() call
                    ↓
            ikabot menu
```

### Output Flow

```
           print() call
                ↓
           TeeStdout
         ╱           ╲
        ↓             ↓
   Terminal       ScreenBuffer
  (always)        (always)
                      ↓
                 OutputControl
                      ↓
               (if monitoring)
                      ↓
                  Telegram
```

### Screen Clear Detection

```
menu() calls → clear() → monkey-patched wrapper
                              ↓
                    original clear() executes
                              ↓
                    ScreenBuffer.mark_cleared()
                              ↓
                      Buffer resets
                              ↓
              /view shows only new content
```

## Behavior

| Event | Action |
|-------|--------|
| Bot starts | QUIET mode, buffer empty |
| Output printed | Terminal shows + buffer stores + Telegram if MONITOR |
| clear() called | Buffer resets (mode unchanged) |
| First message | Auto-enable MONITOR mode |
| /view | Show buffer (since last clear), split if >4096 chars |
| /monitor | Enable Telegram output |
| /mute | Disable Telegram output |
| /stop | Ask bot/all, then shutdown |

## Technical Details

### Monkey-Patching

The `clear()` function is monkey-patched at runtime (in memory only):

```python
import ikabot.helpers.gui as gui

original_clear = gui.clear

def clear_with_detection():
    original_clear()
    screen_buffer.mark_cleared()

gui.clear = clear_with_detection
```

This doesn't modify any files on disk - zero merge conflicts.

### Thread Safety

- `ScreenBuffer`: Uses deque (thread-safe for append/clear)
- `OutputControl`: Uses threading.Lock for mode changes
- `TelegramPoller`: Runs in daemon thread
- `Menu`: Runs in main thread

### Telegram Limits

- Max message length: 4096 characters
- Solution: Auto-split into multiple messages
- Buffer stores unlimited lines between clears

### Link Detection

Automatically makes these patterns clickable:
- `http://example.com`
- `https://example.com/path`
- `192.168.1.1:5000`
- `localhost:8080`
- `example.com:3000`

## Command Configuration

Change command names in `bot.py`:

```python
# At top of bot.py
COMMANDS = {
    "view": "view",
    "monitor": "monitor",
    "mute": "mute",
    "stop": "stop",
    "help": "help",
}
```

## Limitations

- Terminal input and Telegram input are merged (first one wins)
- Screen buffer only captures since last `clear()` call
- Binary/image output not supported (text only)
- Telegram rate limits apply (30 msg/sec for broadcasts)

## Zero-Coupling Design

Complete separation from core:
- Only imports: `command_line.menu()`, `Session`, `sendToBot()`
- No function registry or metadata
- No modifications to `ikabot/` directory
- New functions work automatically

## Contributing

This plugin follows ikabot's lightweight design philosophy:
- Minimal code, maximum functionality
- No new dependencies
- Black formatter (88 char line length)
- Small, focused changes
