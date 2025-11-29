# Feature #08: Telegram Plugin - Zero Coupling Architecture

**Status**: ✅ RECOMMENDED - DEFAULT APPROACH
**Priority**: HIGH
**Difficulty**: 2/10 (even easier than feat-07!)
**Component**: Standalone Plugin (Zero Knowledge of Core)
**Type**: Major Feature - True Plugin Architecture
**Supersedes**: feat-07 (better approach)
**Merge Conflicts**: ✅ ZERO - Perfect for tracking upstream repos

---

## The Problem with feat-07

Even with "complete separation", feat-07 still has coupling:

```python
# plugins/telegram/bot.py
FUNCTION_REGISTRY = {
    "autoPirate": autoPirate,    # ❌ Need to import and map
    "sendResources": sendResources,  # ❌ Need to import and map
    # ... all 25 functions
}

# plugins/telegram/function_metadata.py
FUNCTION_METADATA = {
    "autoPirate": {  # ❌ Need to manually describe
        "steps": [...]
    }
}
```

**Problem**: If core adds new function (e.g., `autoFish`), Telegram breaks until you:
1. Add import statement
2. Add to FUNCTION_REGISTRY
3. Create metadata entry

**Your goal**: Telegram works automatically, no updates needed.

---

## Solution: Terminal Emulator Architecture

### Core Idea: Telegram = Virtual Terminal

Instead of registering functions, **Telegram acts as a terminal emulator**.

```
┌─────────────────────────────────────────────┐
│           Telegram User                      │
└────────────────┬────────────────────────────┘
                 │ Messages
                 ↓
┌─────────────────────────────────────────────┐
│      Telegram Terminal Emulator              │
│  - stdin  = Message queue from Telegram     │
│  - stdout = Send to Telegram                │
│  - Runs command_line.py menu()              │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│       command_line.py (UNCHANGED!)           │
│  - Calls menu()                             │
│  - Shows menu options                       │
│  - Calls read() for input                   │
│  - Thinks it's running in terminal          │
└─────────────────────────────────────────────┘
```

**Key**: Core code literally runs unchanged. It reads from stdin, writes to stdout. Plugin hijacks stdin/stdout.

---

## How It Works: stdin/stdout Hijacking

### Step 1: Intercept stdin

```python
# plugins/telegram/virtual_terminal.py

class TelegramInputStream:
    """Fake stdin that reads from Telegram messages"""

    def __init__(self, message_queue):
        self.queue = message_queue  # Queue of user messages

    def readline(self):
        """Block until user sends message"""
        # Wait for next Telegram message
        message = self.queue.get()  # Blocks
        return message + "\n"

    def fileno(self):
        """Return fake file descriptor"""
        return 99  # Dummy value


class TelegramOutputStream:
    """Fake stdout that sends to Telegram"""

    def __init__(self, session):
        self.session = session
        self.buffer = ""

    def write(self, text):
        """Intercept print() calls"""
        self.buffer += text

        # Send complete lines to Telegram
        if "\n" in self.buffer:
            lines = self.buffer.split("\n")
            for line in lines[:-1]:
                if line.strip():
                    sendToBot(self.session, line)
            self.buffer = lines[-1]

    def flush(self):
        """Send buffered text"""
        if self.buffer.strip():
            sendToBot(self.session, self.buffer)
            self.buffer = ""
```

### Step 2: Run Core Code

```python
# plugins/telegram/bot.py

import sys
from queue import Queue
from ikabot.command_line import menu

class TelegramBot:
    def __init__(self, session):
        self.session = session
        self.message_queue = Queue()

    def handle_user_message(self, text):
        """User sent message - queue it"""
        self.message_queue.put(text)

    def run_interactive_session(self):
        """Run ikabot as if in terminal"""

        # Save original stdin/stdout
        original_stdin = sys.stdin
        original_stdout = sys.stdout

        try:
            # Replace with Telegram versions
            sys.stdin = TelegramInputStream(self.message_queue)
            sys.stdout = TelegramOutputStream(self.session)

            # Just run the menu! It thinks it's CLI!
            menu(self.session)

        finally:
            # Restore original
            sys.stdin = original_stdin
            sys.stdout = original_stdout
```

### Step 3: User Interaction Flow

```
User: /start
Bot: (runs menu(), captures output)
     ┌────────────────────────────┐
     │ Ikabot Menu                │
     │ (0) Exit                   │
     │ (1) Construction list      │
     │ (2) Send resources         │
     │ ...                        │
     │ (17) Auto Pirate           │
     └────────────────────────────┘

User: 17
Bot: (menu() receives "17" from fake stdin)
     (calls autoPirate)
     ⚠️ WARNING ⚠️
     How many pirate missions? (min = 1)

User: 5
Bot: (autoPirate reads "5" from fake stdin)
     Schedule? [y/N]

User: n
Bot: (autoPirate reads "n" from fake stdin)
     Which duration? (1-9)

User: 3
Bot: ✅ Task started!
     (Returns to menu)
```

**Magic**: `autoPirate()` never changed. It called `read()` which called `input()` which read from `sys.stdin` which is now Telegram!

---

## Advantages: Zero Coupling

### 1. No Function Registry ✅

```python
# DON'T NEED THIS:
FUNCTION_REGISTRY = {
    "autoPirate": autoPirate,
    # ...
}
```

Plugin just runs `menu()` - it discovers functions automatically from command_line.py!

### 2. No Function Metadata ✅

```python
# DON'T NEED THIS:
FUNCTION_METADATA = {
    "autoPirate": {
        "steps": [...]
    }
}
```

Plugin doesn't need to know what questions functions will ask - they ask via stdout, get answers via stdin!

### 3. No Import Statements ✅

```python
# DON'T NEED THIS:
from ikabot.function.autoPirate import autoPirate
from ikabot.function.sendResources import sendResources
# ...
```

Plugin only imports `command_line.menu` - one import!

### 4. Automatic Discovery of New Functions ✅

If core adds `autoFish.py`:
1. Add to command_line.py menu (normal process)
2. Telegram works automatically - no plugin changes!

### 5. Works with Future Changes ✅

If autoPirate adds new input step:
1. Update autoPirate.py (normal process)
2. Telegram works automatically - asks new question!

---

## Complete Implementation

### File Structure (Much Simpler!)

```
ikabot/
├── plugins/
│   └── telegram/
│       ├── __init__.py
│       ├── bot.py              # Main bot (100 lines)
│       ├── poller.py           # Telegram polling (50 lines)
│       ├── virtual_terminal.py # stdin/stdout hijack (80 lines)
│       └── formatter.py        # ANSI → Telegram (30 lines)
│
└── telegram_bot.py             # Entry point (30 lines)
```

**Total: ~290 lines** (vs 1000+ lines in feat-07)

### Complete Code

#### 1. Virtual Terminal

```python
# plugins/telegram/virtual_terminal.py

import sys
from queue import Queue, Empty
from ikabot.helpers.botComm import sendToBot

class TelegramInputStream:
    """Acts as sys.stdin, reads from Telegram message queue"""

    def __init__(self, message_queue):
        self.queue = message_queue
        self.buffer = ""

    def readline(self):
        """Read one line (blocks until message available)"""
        if not self.buffer:
            # Wait for next Telegram message
            try:
                message = self.queue.get(timeout=300)  # 5 min timeout
                self.buffer = message + "\n"
            except Empty:
                # Timeout - return empty to trigger exit
                return "\n"

        # Return buffered line
        line = self.buffer
        self.buffer = ""
        return line

    def fileno(self):
        """Return fake file descriptor"""
        return 99


class TelegramOutputStream:
    """Acts as sys.stdout, sends to Telegram"""

    def __init__(self, session, formatter):
        self.session = session
        self.formatter = formatter
        self.buffer = ""
        self.message_buffer = []

    def write(self, text):
        """Intercept print() output"""
        self.buffer += text

        # Split into lines
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)

            if line.strip():
                # Convert ANSI codes
                telegram_line = self.formatter.convert(line)
                self.message_buffer.append(telegram_line)

                # Send batch of lines (avoid Telegram spam limits)
                if len(self.message_buffer) >= 10:
                    self.flush()

    def flush(self):
        """Send buffered lines to Telegram"""
        if self.message_buffer:
            # Combine lines
            message = "\n".join(self.message_buffer)
            sendToBot(self.session, message)
            self.message_buffer = []


class VirtualTerminal:
    """Context manager for terminal hijacking"""

    def __init__(self, session, formatter):
        self.session = session
        self.formatter = formatter
        self.message_queue = Queue()

        self.original_stdin = None
        self.original_stdout = None

        self.fake_stdin = TelegramInputStream(self.message_queue)
        self.fake_stdout = TelegramOutputStream(session, formatter)

    def __enter__(self):
        """Hijack stdin/stdout"""
        self.original_stdin = sys.stdin
        self.original_stdout = sys.stdout

        sys.stdin = self.fake_stdin
        sys.stdout = self.fake_stdout

        return self

    def __exit__(self, *args):
        """Restore stdin/stdout"""
        sys.stdin = self.original_stdin
        sys.stdout = self.original_stdout

        # Flush remaining output
        self.fake_stdout.flush()

    def send_input(self, text):
        """Queue user input"""
        self.message_queue.put(text)
```

#### 2. Main Bot

```python
# plugins/telegram/bot.py

import threading
from queue import Queue
from ikabot.command_line import menu
from plugins.telegram.virtual_terminal import VirtualTerminal
from plugins.telegram.formatter import ANSIToTelegramFormatter
from plugins.telegram.poller import TelegramPoller
from ikabot.helpers.botComm import sendToBot

class TelegramBot:
    """Telegram bot that runs ikabot as virtual terminal"""

    def __init__(self, session):
        self.session = session
        self.formatter = ANSIToTelegramFormatter()
        self.virtual_terminal = None
        self.menu_thread = None
        self.running = False

        # Start poller
        self.poller = TelegramPoller(session, self.handle_message)

    def start(self):
        """Start bot"""
        self.running = True

        # Start polling
        self.poller.start()

        # Send welcome
        sendToBot(self.session, "🤖 Ikabot Telegram interface ready!")
        sendToBot(self.session, "Type any menu option number to start")

        # Start interactive menu in thread
        self.menu_thread = threading.Thread(
            target=self._run_menu_loop,
            daemon=True
        )
        self.menu_thread.start()

    def stop(self):
        """Stop bot"""
        self.running = False
        self.poller.stop()

        if self.menu_thread:
            self.menu_thread.join(timeout=5)

    def handle_message(self, update):
        """Handle incoming Telegram message"""
        if "message" not in update:
            return

        text = update["message"].get("text", "")

        if not text:
            return

        # Send input to virtual terminal
        if self.virtual_terminal:
            self.virtual_terminal.send_input(text)

    def _run_menu_loop(self):
        """Run menu in virtual terminal (runs in thread)"""

        while self.running:
            try:
                # Create virtual terminal
                self.virtual_terminal = VirtualTerminal(
                    self.session,
                    self.formatter
                )

                # Run menu with hijacked stdin/stdout
                with self.virtual_terminal:
                    menu(self.session)

                # Menu exited (user chose exit)
                sendToBot(self.session, "Session ended. Type anything to restart.")

            except Exception as e:
                sendToBot(self.session, f"Error: {str(e)}")
                sendToBot(self.session, "Type anything to restart.")
```

#### 3. Poller (Same as feat-07)

```python
# plugins/telegram/poller.py

import time
import threading
from requests import get

class TelegramPoller:
    """Polls Telegram for updates"""

    def __init__(self, session, message_handler):
        self.session = session
        self.message_handler = message_handler
        self.running = False
        self.thread = None
        self.last_update_id = 0

        session_data = session.getSessionData()
        self.bot_token = session_data["shared"]["telegram"]["botToken"]

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False

    def _poll_loop(self):
        while self.running:
            try:
                response = get(
                    f"https://api.telegram.org/bot{self.bot_token}/getUpdates",
                    params={
                        "offset": self.last_update_id + 1,
                        "timeout": 30
                    },
                    timeout=35
                ).json()

                if response.get("ok") and response.get("result"):
                    for update in response["result"]:
                        self.last_update_id = update["update_id"]
                        self.message_handler(update)

            except Exception as e:
                print(f"Polling error: {e}")
                time.sleep(5)

            time.sleep(1)
```

#### 4. Formatter (Same as feat-07)

```python
# plugins/telegram/formatter.py

import re

class ANSIToTelegramFormatter:
    """Convert ANSI escape codes to Telegram Markdown"""

    def __init__(self):
        self.patterns = {
            r'\033\[1;91m': '*',  # Bright red → Bold
            r'\033\[1;92m': '*',  # Bright green → Bold
            r'\033\[0m': '*',     # Reset → Close
            r'\033\[[0-9;]+m': '', # Remove others
        }

    def convert(self, text):
        """Convert ANSI to Telegram"""
        result = text
        for pattern, replacement in self.patterns.items():
            result = re.sub(pattern, replacement, result)
        return result
```

#### 5. Entry Point

```python
# telegram_bot.py

#!/usr/bin/env python3
"""Telegram Bot for Ikabot"""

import sys
import time
import signal
from ikabot.web.session import Session
from plugins.telegram.bot import TelegramBot

def main():
    print("Starting Ikabot Telegram Bot...")

    session = Session()
    if not session.logged:
        print("❌ Not logged in")
        return

    bot = TelegramBot(session)

    def signal_handler(sig, frame):
        print("\nStopping...")
        bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    bot.start()
    print("✅ Bot running")

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
```

---

## Comparison: feat-07 vs feat-08

| Aspect | feat-07 | feat-08 |
|--------|---------|---------|
| **Lines of code** | ~1000 | **~290** |
| **Function registry** | Required | **None** |
| **Function metadata** | Required | **None** |
| **Import functions** | All 25 | **Just menu()** |
| **New function added** | Update registry + metadata | **Works automatically** |
| **Function changed** | Update metadata | **Works automatically** |
| **Coupling to core** | Medium | **ZERO** |
| **Complexity** | 3/10 | **2/10** |

---

## How It Achieves Goals

### Goal 1: No changes in existing codebase ✅

**feat-08**: Zero changes, not even optional parameters

### Goal 2: Additions won't need fixing in Telegram ✅

**Example: New function added**

1. Developer adds `ikabot/function/autoFish.py`
2. Developer adds to `command_line.py` menu:
   ```python
   print("(26) Auto Fish")
   menu_actions[26] = autoFish
   ```
3. **Telegram works immediately** - no plugin changes!

**Example: Function input changed**

1. Developer modifies `autoPirate.py` to ask new question:
   ```python
   target_level = read(min=1, max=15, msg="Target fortress level?")
   ```
2. **Telegram works immediately** - asks new question!

### Goal 3: Complete independence ✅

Plugin only knows:
- How to poll Telegram
- How to hijack stdin/stdout
- How to convert ANSI codes

Plugin doesn't know:
- What functions exist
- What questions they ask
- What inputs they need
- What menu structure is

**Core and plugin are truly independent.**

---

## Limitations & Solutions

### Limitation 1: Inline Keyboards

**Problem**: Virtual terminal approach can't use Telegram inline keyboards (buttons)

**Solution**: Still better UX than registry approach because:
- User just types numbers (familiar from CLI)
- No need to create keyboard layouts
- Works with any menu structure automatically

**Optional Enhancement**: Add keyboard generator that parses menu output and creates buttons dynamically.

### Limitation 2: No Back Button

**Problem**: CLI doesn't have back button, neither does Telegram version

**Solution**: This is CLI limitation, not plugin limitation. Once CLI adds back buttons (see feat-04), Telegram inherits them automatically!

### Limitation 3: Process Table Display

**Problem**: CLI shows process table at top of screen, Telegram can't do this

**Solution**: Add special command `/tasks` that prints process table when requested. This is enhancement, not blocker.

---

## Implementation Timeline

| Phase | Effort |
|-------|--------|
| 1. VirtualTerminal class | 1 day |
| 2. TelegramBot integration | 1 day |
| 3. Poller + Formatter | 1 day |
| 4. Testing | 1 day |

**Total: 4 days** (vs 16 days for feat-07)

---

## Migration Path

### From feat-07 to feat-08

If you already implemented feat-07:

1. Delete `function_metadata.py` - not needed
2. Delete `FUNCTION_REGISTRY` - not needed
3. Replace executor/conversation with VirtualTerminal
4. Simplify bot.py to just run menu()

### Starting Fresh

Just implement feat-08 directly - much simpler!

---

## Proof of Concept Test

```python
# test_virtual_terminal.py

from queue import Queue
from plugins.telegram.virtual_terminal import VirtualTerminal
from plugins.telegram.formatter import ANSIToTelegramFormatter

# Simulate user sending "5" then "n" then "3"
queue = Queue()
queue.put("5")
queue.put("n")
queue.put("3")

# Create terminal
terminal = VirtualTerminal(session, ANSIToTelegramFormatter())
terminal.message_queue = queue

# Hijack stdin/stdout
with terminal:
    # Run autoPirate - it will read from queue!
    autoPirate(session, event, sys.stdin.fileno(), [])

# Output was sent to Telegram via sendToBot()
# Function never knew it wasn't in real terminal!
```

---

## Why This is Better

### feat-07 Approach (Registry)
```python
# Telegram needs to know everything:
- Import all 25 functions
- Map them in registry
- Describe all inputs in metadata
- Update when anything changes

# Plugin is AWARE of core
```

### feat-08 Approach (Terminal)
```python
# Telegram knows nothing:
- Import only menu()
- Hijack stdin/stdout
- Let core do its thing

# Plugin is UNAWARE of core
```

**This is true plugin architecture.**

---

## Final Architecture Diagram

```
┌─────────────────────────────────────────────┐
│         User (via Telegram app)              │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│        Telegram Bot API                      │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│   TelegramBot (poller + virtual terminal)   │
│   - Polls for messages                      │
│   - Queues input                            │
│   - Intercepts output                       │
└────────────────┬────────────────────────────┘
                 │ sys.stdin/stdout hijacked
                 ↓
┌─────────────────────────────────────────────┐
│        command_line.menu()                   │
│        (COMPLETELY UNCHANGED)                │
│        - Shows menu                          │
│        - Calls functions                     │
│        - Uses read()/print()                 │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│     Functions (autoPirate, etc)              │
│     (COMPLETELY UNCHANGED)                   │
│     - Call read()                            │
│     - Call print()                           │
│     - Never know Telegram exists             │
└─────────────────────────────────────────────┘
```

**Zero coupling. True independence.**

---

## Recommendation

**Implement feat-08 instead of feat-07** because:

1. ✅ 70% less code (290 vs 1000 lines)
2. ✅ 75% less time (4 vs 16 days)
3. ✅ Zero coupling (vs medium coupling)
4. ✅ True independence (vs registry dependency)
5. ✅ Simpler to maintain
6. ✅ Automatically supports future changes

**This is the right architecture.**

---

**Created**: 2025-11-12
**Status**: Ready for Implementation
**Supersedes**: feat-07
**Recommendation**: ✅ **Implement this approach**
