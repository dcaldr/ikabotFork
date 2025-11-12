# Feature #07: Telegram Plugin - Complete Separation Implementation Plan

**Status**: Implementation Ready
**Priority**: HIGH
**Difficulty**: 3/10 (with complete separation approach)
**Component**: Plugin Module (Zero Core Changes)
**Type**: Major Feature - Telegram Bot Interface
**Builds On**: feat-06-telegram-plugin-implementation-plan.md

---

## Key Principles: Complete Separation

### What "Complete Separation" Means

1. ✅ **ZERO changes to core functions** - All 25+ functions remain unchanged
2. ✅ **ZERO changes to command_line.py** - CLI untouched
3. ✅ **ZERO changes to pedirInfo.py** - Input system unchanged
4. ✅ **Plugin uses existing APIs only** - predetermined_input, sendToBot()
5. ✅ **Plugin is removable** - Delete plugins/ folder, ikabot still works

**Core never knows Telegram exists.**

---

## Architecture: How Complete Separation Works

### The Magic: predetermined_input + Output Capture

```
┌─────────────────────────────────────────────────────────────┐
│                    Telegram User                             │
└───────────────────────────┬─────────────────────────────────┘
                            │ Messages
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Telegram Plugin                             │
│  1. Receives "Start Auto-Pirate"                            │
│  2. Asks user questions via Telegram                        │
│  3. Collects: [5, "n", 3, ...]                              │
│  4. Populates config.predetermined_input = [5, "n", 3]      │
│  5. Redirects stdout to capture print()                     │
│  6. Calls autoPirate() → reads from predetermined_input!    │
│  7. Captures output, converts ANSI → Telegram Markdown      │
│  8. Sends formatted output to Telegram                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│           Core Functions (COMPLETELY UNCHANGED!)             │
│  - autoPirate() reads from predetermined_input              │
│  - Prints to stdout (captured by plugin)                    │
│  - Uses ANSI colors (converted by plugin)                   │
│  - NO CHANGES NEEDED                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Problem 1: Formatting Conversion (ANSI → Telegram)

### Current State

Core functions use ANSI escape codes:
```python
# ikabot/helpers/gui.py
Colours = {
    "red": "\033[1;91m",
    "green": "\033[1;92m",
    "yellow": "\033[1;93m",
}

print(f"{Colours['red']}⚠️ WARNING ⚠️{Colours['reset']}")
```

### Plugin Solution: Convert ANSI to Telegram Markdown

```python
# plugins/telegram/formatter.py

import re

class ANSIToTelegramFormatter:
    """Converts ANSI escape codes to Telegram Markdown"""

    def __init__(self):
        self.ansi_patterns = {
            # Bold/Bright colors → Bold in Telegram
            r'\033\[1;91m': '*',  # Bright red → Bold
            r'\033\[1;92m': '*',  # Bright green → Bold
            r'\033\[1;93m': '*',  # Bright yellow → Bold
            r'\033\[1;94m': '*',  # Bright blue → Bold

            # Normal colors → Italic in Telegram
            r'\033\[91m': '_',    # Red → Italic
            r'\033\[92m': '_',    # Green → Italic
            r'\033\[93m': '_',    # Yellow → Italic

            # Reset → Close formatting
            r'\033\[0m': '*',     # or '_' depending on context

            # Generic ANSI escape code pattern (catch-all)
            r'\033\[[0-9;]+m': '',  # Remove any other codes
        }

    def convert(self, ansi_text):
        """Convert ANSI text to Telegram Markdown"""
        result = ansi_text

        for pattern, replacement in self.ansi_patterns.items():
            result = re.sub(pattern, replacement, result)

        return result

    def strip_ansi(self, text):
        """Remove all ANSI codes (fallback if conversion fails)"""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
```

**Result**: Core uses ANSI, Telegram sees Markdown. Zero core changes. ✅

---

## Problem 2: Multi-Step Conversations

### How predetermined_input Solves It

**CLI Flow** (synchronous):
```python
def autoPirate(session, event, stdin_fd, predetermined_input):
    count = read(min=1)      # BLOCKS, waits for input
    schedule = read(...)     # BLOCKS again
    duration = read(...)     # BLOCKS again
    # All data collected, start task
```

**Telegram Flow** (asynchronous, but same function!):
```python
# User message 1: "Start Auto-Pirate"
telegram_bot.ask_user("How many missions?")

# User message 2: "5"
telegram_bot.save_answer("5")
telegram_bot.ask_user("Schedule? (y/n)")

# User message 3: "n"
telegram_bot.save_answer("n")
telegram_bot.ask_user("Duration? (1-9)")

# User message 4: "3"
telegram_bot.save_answer("3")

# Now have all answers: ["5", "n", "3"]
config.predetermined_input = [5, "n", 3]

# Call function - it reads from predetermined_input instead of input()!
autoPirate(session, event, sys.stdin.fileno(), config.predetermined_input)
```

**Key**: `pedirInfo.py:read()` already checks `predetermined_input` first:
```python
# ikabot/helpers/pedirInfo.py:62-63
if len(config.predetermined_input) != 0:
    return config.predetermined_input.pop(0)
```

This ALREADY EXISTS! Zero changes needed. ✅

---

## Problem 3: Knowing What Questions to Ask

### Solution: Function Metadata Registry

Create metadata that describes each function's inputs:

```python
# plugins/telegram/function_metadata.py

FUNCTION_METADATA = {
    "autoPirate": {
        "name": "Auto Pirate",
        "description": "Automatically execute pirate missions",
        "icon": "🏴‍☠️",
        "steps": [
            {
                "prompt": "How many pirate missions should I do?",
                "validation": {"type": "int", "min": 1},
                "save_as": "pirate_count"
            },
            {
                "prompt": "Should I schedule the missions? (y/n)",
                "validation": {"type": "choice", "values": ["y", "Y", "n", "N", ""]},
                "save_as": "schedule_choice"
            },
            {
                "prompt": "Which mission duration? (1=30min, 2=1h, ...)",
                "validation": {"type": "int", "min": 1, "max": 9},
                "save_as": "mission_duration",
                "condition": {"field": "schedule_choice", "value": "n"}
            },
            # ... more steps
        ]
    },

    "sendResources": {
        "name": "Send Resources",
        "icon": "📦",
        "steps": [
            # ... steps
        ]
    },

    # ... all other functions
}
```

**Plugin uses this to**:
1. Know what questions to ask
2. Validate user input
3. Know when all inputs collected
4. Build predetermined_input list

**Core never sees this metadata.** ✅

---

## Implementation Structure

### File Structure

```
ikabot/
├── plugins/                          # NEW - Plugin directory
│   ├── __init__.py
│   └── telegram/                     # NEW - Telegram plugin
│       ├── __init__.py
│       ├── bot.py                    # Main bot coordinator
│       ├── poller.py                 # Telegram polling loop
│       ├── conversation.py           # Multi-step conversation manager
│       ├── executor.py               # Function executor with output capture
│       ├── formatter.py              # ANSI → Telegram converter
│       ├── menu.py                   # Telegram inline keyboards
│       └── function_metadata.py      # Function input descriptions
│
├── helpers/                          # UNCHANGED
│   ├── botComm.py                    # Already has sendToBot()!
│   ├── pedirInfo.py                  # Already has predetermined_input support!
│   └── ...
│
├── function/                         # UNCHANGED
│   ├── autoPirate.py                 # No changes
│   ├── sendResources.py              # No changes
│   └── ...
│
└── command_line.py                   # UNCHANGED
```

---

## Phase 1: Output Capture & Formatting (2 days)

### Deliverables

1. **Output Capturer** (`plugins/telegram/executor.py`)
2. **ANSI Formatter** (`plugins/telegram/formatter.py`)
3. **Test with simple function** (getStatus)

### Code: Output Capturer

```python
# plugins/telegram/executor.py

import sys
import io
import contextlib
from ikabot import config

class FunctionExecutor:
    """Executes core functions with output capture"""

    def __init__(self, formatter):
        self.formatter = formatter

    def execute_with_capture(self, func, session, event, predetermined_inputs):
        """
        Execute a function and capture its output

        Args:
            func: Function reference (e.g., autoPirate)
            session: Session object
            event: multiprocessing.Event
            predetermined_inputs: List of inputs to populate

        Returns:
            Captured output as string
        """
        # Populate predetermined_input
        config.predetermined_input = predetermined_inputs.copy()

        # Capture stdout
        captured_output = io.StringIO()

        with contextlib.redirect_stdout(captured_output):
            try:
                # Call the function - it reads from predetermined_input!
                func(
                    session,
                    event,
                    sys.stdin.fileno(),
                    config.predetermined_input
                )
            except Exception as e:
                # Capture errors
                print(f"Error: {str(e)}")

        # Get captured text
        output = captured_output.getvalue()

        # Convert ANSI to Telegram
        telegram_output = self.formatter.convert(output)

        return telegram_output
```

### Test Plan for Phase 1

```python
# Test 1: Capture simple output
def test_capture():
    executor = FunctionExecutor(ANSIToTelegramFormatter())

    # getStatus needs no inputs
    output = executor.execute_with_capture(
        getStatus,
        session,
        event,
        []
    )

    assert len(output) > 0
    assert "\033[" not in output  # No ANSI codes

# Test 2: Format conversion
def test_ansi_conversion():
    formatter = ANSIToTelegramFormatter()

    ansi_text = "\033[1;91mWARNING\033[0m"
    result = formatter.convert(ansi_text)

    assert result == "*WARNING*"  # Bold in Telegram

# Test 3: Execute with predetermined_input
def test_with_inputs():
    executor = FunctionExecutor(ANSIToTelegramFormatter())

    # simulateAttack needs 2 inputs: city index, times
    output = executor.execute_with_capture(
        simulateAttack,
        session,
        event,
        [1, 5]  # City 1, simulate 5 times
    )

    assert "simulation" in output.lower()
```

---

## Phase 2: Telegram Polling & Messaging (3 days)

### Deliverables

1. **Telegram Poller** (`plugins/telegram/poller.py`)
2. **Basic Message Handler** (`plugins/telegram/bot.py`)
3. **Test bidirectional communication**

### Code: Telegram Poller

```python
# plugins/telegram/poller.py

import time
import threading
from requests import get
from ikabot.helpers.botComm import sendToBot

class TelegramPoller:
    """Polls Telegram for updates (messages from user)"""

    def __init__(self, session, message_handler):
        self.session = session
        self.message_handler = message_handler
        self.running = False
        self.thread = None
        self.last_update_id = 0

        # Get bot token from session
        session_data = session.getSessionData()
        self.bot_token = session_data["shared"]["telegram"]["botToken"]
        self.chat_id = int(session_data["shared"]["telegram"]["chatId"])

    def start(self):
        """Start polling in background thread"""
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop polling"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _poll_loop(self):
        """Main polling loop"""
        while self.running:
            try:
                # Long polling (timeout 30s)
                response = get(
                    f"https://api.telegram.org/bot{self.bot_token}/getUpdates",
                    params={
                        "offset": self.last_update_id + 1,
                        "timeout": 30,
                        "allowed_updates": ["message", "callback_query"]
                    },
                    timeout=35
                ).json()

                if response.get("ok") and response.get("result"):
                    for update in response["result"]:
                        self.last_update_id = update["update_id"]

                        # Pass to message handler
                        self.message_handler(update)

            except Exception as e:
                print(f"Telegram polling error: {e}")
                time.sleep(5)

            time.sleep(1)  # Brief pause between polls
```

### Code: Basic Bot

```python
# plugins/telegram/bot.py

from ikabot.helpers.botComm import sendToBot

class TelegramBot:
    """Main bot coordinator"""

    def __init__(self, session):
        self.session = session
        self.poller = TelegramPoller(session, self.handle_update)

        # Get chat ID
        session_data = session.getSessionData()
        self.chat_id = int(session_data["shared"]["telegram"]["chatId"])

    def start(self):
        """Start the bot"""
        self.poller.start()
        sendToBot(self.session, "🤖 Ikabot Telegram interface ready!")
        sendToBot(self.session, "Type /menu to see options")

    def stop(self):
        """Stop the bot"""
        self.poller.stop()

    def handle_update(self, update):
        """Handle incoming Telegram update"""
        if "message" in update:
            self.handle_message(update["message"])
        elif "callback_query" in update:
            self.handle_button_click(update["callback_query"])

    def handle_message(self, message):
        """Handle text message from user"""
        text = message.get("text", "")

        if text == "/menu":
            self.show_menu()
        elif text == "/help":
            sendToBot(self.session, "Available commands:\n/menu - Show menu\n/tasks - List running tasks\n/cancel - Cancel current conversation")
        else:
            sendToBot(self.session, f"You said: {text}")

    def handle_button_click(self, callback_query):
        """Handle inline keyboard button click"""
        data = callback_query.get("data", "")
        sendToBot(self.session, f"Button clicked: {data}")

    def show_menu(self):
        """Show main menu (placeholder)"""
        sendToBot(self.session, "Menu will be here!")
```

### Test Plan for Phase 2

```bash
# Manual test:
1. Run: python plugins/telegram/test_bot.py
2. Send message "/menu" in Telegram
3. Verify bot responds
4. Send message "Hello"
5. Verify bot echoes
6. Press Ctrl+C to stop
7. Verify graceful shutdown
```

---

## Phase 3: Conversation State Manager (3 days)

### Deliverables

1. **Conversation State Manager** (`plugins/telegram/conversation.py`)
2. **Integration with metadata** (function_metadata.py)
3. **Test multi-step flow**

### Code: Conversation Manager

```python
# plugins/telegram/conversation.py

from plugins.telegram.function_metadata import FUNCTION_METADATA

class ConversationState:
    """Manages multi-step conversations per user"""

    def __init__(self):
        # For 1 user/1 bot, we only need single state
        # For multi-user: self.states = {}  # chat_id -> state
        self.current_function = None
        self.current_step = 0
        self.collected_answers = []
        self.metadata = None

    def start_conversation(self, function_name):
        """Start a new conversation for a function"""
        if function_name not in FUNCTION_METADATA:
            raise ValueError(f"Unknown function: {function_name}")

        self.current_function = function_name
        self.current_step = 0
        self.collected_answers = []
        self.metadata = FUNCTION_METADATA[function_name]

    def get_current_question(self):
        """Get the current question to ask user"""
        if not self.metadata:
            return None

        steps = self.metadata["steps"]

        if self.current_step >= len(steps):
            return None  # All questions answered

        step = steps[self.current_step]

        # Check if this step has a condition
        if "condition" in step:
            condition = step["condition"]
            # Find the answer for the condition field
            # (simplified - in real implementation, track answers by name)
            if not self._condition_met(condition):
                # Skip this step
                self.current_step += 1
                return self.get_current_question()

        return step["prompt"]

    def save_answer(self, answer):
        """Save user's answer and move to next step"""
        self.collected_answers.append(answer)
        self.current_step += 1

    def is_complete(self):
        """Check if all questions answered"""
        if not self.metadata:
            return False

        # Simple check: current step >= total steps
        return self.current_step >= len(self.metadata["steps"])

    def get_all_answers(self):
        """Get collected answers as list for predetermined_input"""
        return self.collected_answers.copy()

    def clear(self):
        """Clear conversation state"""
        self.current_function = None
        self.current_step = 0
        self.collected_answers = []
        self.metadata = None

    def _condition_met(self, condition):
        """Check if a condition is met (simplified)"""
        # Real implementation would track answers by field name
        return True
```

---

## Phase 4: Menu System & Integration (3 days)

### Deliverables

1. **Inline Keyboard Menu** (`plugins/telegram/menu.py`)
2. **Function Registry** (mapping menu options to functions)
3. **Full integration** (bot.py connects everything)

### Code: Menu System

```python
# plugins/telegram/menu.py

import json
from requests import get
from plugins.telegram.function_metadata import FUNCTION_METADATA

class TelegramMenu:
    """Manages Telegram inline keyboard menus"""

    def __init__(self, session):
        self.session = session
        session_data = session.getSessionData()
        self.bot_token = session_data["shared"]["telegram"]["botToken"]
        self.chat_id = int(session_data["shared"]["telegram"]["chatId"])

    def send_main_menu(self):
        """Send main menu with inline keyboard"""

        # Build keyboard from function metadata
        keyboard_buttons = []

        for func_name, metadata in FUNCTION_METADATA.items():
            button = {
                "text": f"{metadata['icon']} {metadata['name']}",
                "callback_data": f"func:{func_name}"
            }
            keyboard_buttons.append([button])

        # Add utility buttons
        keyboard_buttons.append([
            {"text": "📋 Tasks", "callback_data": "cmd:tasks"},
            {"text": "❌ Cancel", "callback_data": "cmd:cancel"}
        ])

        keyboard = {"inline_keyboard": keyboard_buttons}

        # Send via Telegram API
        get(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            params={
                "chat_id": self.chat_id,
                "text": "🤖 *Ikabot Menu*\n\nChoose an action:",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(keyboard)
            }
        )
```

### Complete Integration

```python
# plugins/telegram/bot.py (updated)

from plugins.telegram.poller import TelegramPoller
from plugins.telegram.conversation import ConversationState
from plugins.telegram.executor import FunctionExecutor
from plugins.telegram.formatter import ANSIToTelegramFormatter
from plugins.telegram.menu import TelegramMenu
from ikabot.helpers.botComm import sendToBot

# Import core functions
from ikabot.function.autoPirate import autoPirate
from ikabot.function.sendResources import sendResources
# ... import all functions

FUNCTION_REGISTRY = {
    "autoPirate": autoPirate,
    "sendResources": sendResources,
    # ... map all functions
}

class TelegramBot:
    """Complete Telegram bot with all features"""

    def __init__(self, session):
        self.session = session
        self.poller = TelegramPoller(session, self.handle_update)
        self.conversation = ConversationState()
        self.executor = FunctionExecutor(ANSIToTelegramFormatter())
        self.menu = TelegramMenu(session)

        session_data = session.getSessionData()
        self.chat_id = int(session_data["shared"]["telegram"]["chatId"])

    def start(self):
        """Start the bot"""
        self.poller.start()
        sendToBot(self.session, "🤖 Ikabot Telegram interface ready!")
        self.menu.send_main_menu()

    def handle_update(self, update):
        """Handle incoming update"""
        if "message" in update:
            self.handle_message(update["message"])
        elif "callback_query" in update:
            self.handle_button_click(update["callback_query"])

    def handle_button_click(self, callback_query):
        """Handle button click"""
        data = callback_query["data"]

        if data.startswith("func:"):
            # Function selected
            function_name = data.split(":", 1)[1]
            self.start_function_conversation(function_name)

        elif data == "cmd:tasks":
            self.show_tasks()

        elif data == "cmd:cancel":
            self.conversation.clear()
            sendToBot(self.session, "Cancelled.")
            self.menu.send_main_menu()

    def handle_message(self, message):
        """Handle text message"""
        text = message.get("text", "")

        # Check if in active conversation
        if self.conversation.current_function:
            # This is an answer to current question
            self.conversation.save_answer(text)
            self.continue_conversation()
        else:
            # Not in conversation
            if text == "/menu":
                self.menu.send_main_menu()
            elif text == "/tasks":
                self.show_tasks()
            else:
                sendToBot(self.session, "Type /menu to see options")

    def start_function_conversation(self, function_name):
        """Start conversation for a function"""
        self.conversation.start_conversation(function_name)

        # Ask first question
        question = self.conversation.get_current_question()
        if question:
            sendToBot(self.session, question)
        else:
            # No questions (shouldn't happen)
            sendToBot(self.session, "Error: No questions defined")

    def continue_conversation(self):
        """Continue conversation after receiving answer"""
        if self.conversation.is_complete():
            # All answers collected - execute function!
            self.execute_function()
        else:
            # Ask next question
            question = self.conversation.get_current_question()
            sendToBot(self.session, question)

    def execute_function(self):
        """Execute function with collected answers"""
        function_name = self.conversation.current_function
        answers = self.conversation.get_all_answers()

        sendToBot(self.session, "⏳ Starting task...")

        # Get function reference
        func = FUNCTION_REGISTRY.get(function_name)

        if not func:
            sendToBot(self.session, f"Error: Function {function_name} not found")
            self.conversation.clear()
            return

        # Execute with output capture
        try:
            output = self.executor.execute_with_capture(
                func,
                self.session,
                event,
                answers
            )

            # Send output to user
            if output:
                sendToBot(self.session, output)

            sendToBot(self.session, "✅ Task started!")

        except Exception as e:
            sendToBot(self.session, f"❌ Error: {str(e)}")

        finally:
            # Clear conversation
            self.conversation.clear()

            # Show menu again
            self.menu.send_main_menu()

    def show_tasks(self):
        """Show running tasks"""
        from ikabot.helpers.process import updateProcessList

        process_list = updateProcessList(self.session)

        if not process_list:
            sendToBot(self.session, "No tasks running")
            return

        msg = "📋 *Running Tasks*\n\n"
        for proc in process_list:
            msg += f"• {proc['action']}\n"
            msg += f"  Status: {proc['status']}\n\n"

        sendToBot(self.session, msg)
```

---

## Phase 5: Function Metadata Creation (2 days)

### Deliverable

Complete `function_metadata.py` with all 25 functions described.

### Template

```python
# plugins/telegram/function_metadata.py

FUNCTION_METADATA = {
    "autoPirate": {
        "name": "Auto Pirate",
        "description": "Automatically execute pirate missions",
        "icon": "🏴‍☠️",
        "steps": [
            {
                "prompt": "How many pirate missions should I do? (min = 1)",
                "validation": {"type": "int", "min": 1},
                "save_as": "pirate_count"
            },
            {
                "prompt": "Do you want to schedule the task? [y/N]",
                "validation": {"type": "choice", "values": ["y", "Y", "n", "N", ""]},
                "save_as": "schedule_choice"
            },
            # ... more steps based on autoPirate.py flow
        ]
    },

    # ... repeat for all 25 functions
}
```

**How to create metadata for each function:**

1. Read function source (e.g., `ikabot/function/autoPirate.py`)
2. Find all `read()` calls
3. Extract prompt text, validation params
4. Create step entry in metadata
5. Test: Send inputs via Telegram, verify function works

---

## Phase 6: Testing & Polish (3 days)

### Test Suite

```python
# tests/test_telegram_plugin.py

def test_phase1_output_capture():
    """Test output capture and ANSI conversion"""
    # ... tests

def test_phase2_polling():
    """Test Telegram polling"""
    # ... tests

def test_phase3_conversation():
    """Test multi-step conversation"""
    # ... tests

def test_phase4_integration():
    """Test full integration"""
    # ... tests

def test_all_functions():
    """Test all 25 functions work via Telegram"""
    for func_name in FUNCTION_REGISTRY:
        # Test with predetermined_input
        pass
```

### Manual Testing Checklist

- [ ] Bot starts successfully
- [ ] /menu shows menu with all functions
- [ ] Click function button → asks first question
- [ ] Answer question → asks next question
- [ ] Complete conversation → function executes
- [ ] Output formatted correctly (no ANSI codes)
- [ ] Bold/colors converted to Telegram markdown
- [ ] /tasks shows running processes
- [ ] /cancel aborts conversation
- [ ] Multiple conversations in sequence work
- [ ] Invalid input is rejected gracefully
- [ ] CLI still works perfectly (untouched)

---

## Timeline Summary

| Phase | Effort | Cumulative |
|-------|--------|------------|
| 1. Output Capture & Formatting | 2 days | 2 days |
| 2. Telegram Polling | 3 days | 5 days |
| 3. Conversation Manager | 3 days | 8 days |
| 4. Menu & Integration | 3 days | 11 days |
| 5. Function Metadata | 2 days | 13 days |
| 6. Testing & Polish | 3 days | 16 days |

**Total: 16 days (2-3 weeks)**

---

## Proof of Concept: Test with One Function

### PoC Goal

Verify complete separation works with `autoPirate`:

1. User clicks "🏴‍☠️ Auto Pirate" in Telegram
2. Bot asks questions one by one
3. User answers via Telegram messages
4. Bot populates `predetermined_input`
5. Bot calls `autoPirate()` (unchanged!)
6. Bot captures output, converts ANSI
7. Bot sends result to Telegram
8. Task runs in background

**If PoC succeeds:** Approach validated, continue with all functions
**If PoC fails:** Re-evaluate strategy

---

## Entry Point: Standalone Script

```python
# telegram_bot.py (project root)

#!/usr/bin/env python3
"""
Standalone Telegram Bot for Ikabot
Run with: python telegram_bot.py
"""

import sys
import time
import signal
from ikabot.web.session import Session
from plugins.telegram.bot import TelegramBot

def main():
    print("Starting Ikabot Telegram Bot...")

    # Create session
    session = Session()

    if not session.logged:
        print("❌ Failed to login")
        print("Make sure you've run ikabot CLI at least once to save session")
        return

    # Check if Telegram configured
    session_data = session.getSessionData()
    if "telegram" not in session_data.get("shared", {}):
        print("❌ Telegram not configured")
        print("Run ikabot CLI and configure Telegram first (Donate menu → Configure Telegram)")
        return

    # Create and start bot
    bot = TelegramBot(session)

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nStopping bot...")
        bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Start bot
    bot.start()

    print("✅ Bot running")
    print("Press Ctrl+C to stop")

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping bot...")
        bot.stop()

if __name__ == "__main__":
    main()
```

**Usage:**
```bash
python telegram_bot.py
# Bot runs in foreground, press Ctrl+C to stop
```

---

## Success Criteria

### Must Have ✅

- [ ] Zero changes to core functions
- [ ] Zero changes to command_line.py
- [ ] All functions accessible via Telegram
- [ ] Multi-step conversations work
- [ ] ANSI → Telegram formatting works
- [ ] predetermined_input mechanism works
- [ ] CLI continues to work perfectly
- [ ] Plugin is removable

### Should Have 📋

- [ ] /menu command with inline keyboards
- [ ] /tasks command shows running processes
- [ ] /cancel command aborts conversation
- [ ] Error messages formatted nicely
- [ ] Progress indicators for long tasks
- [ ] Metadata for all 25 functions

### Nice to Have 🌟

- [ ] Conversation timeout (15 min)
- [ ] Help text for each function
- [ ] Emoji indicators for status
- [ ] Session persistence across bot restarts
- [ ] Multi-user support (if needed later)

---

## CONTRIBUTING.md Compliance

✅ **Lightweight design**: Plugin is optional, removable, ~500 lines total
✅ **No new dependencies**: Uses existing `requests`, `sendToBot()`, `predetermined_input`
✅ **Minimal changes**: ZERO changes to core code
✅ **Python 3.8+**: Uses standard library (threading, io, contextlib, re)
✅ **Black formatting**: Will format all plugin code

---

## Risk Mitigation

### Risk 1: Output capture doesn't work
**Mitigation**: Fallback to parsing session.setStatus() if stdout capture fails

### Risk 2: predetermined_input has edge cases
**Mitigation**: Test with all 25 functions, fix as needed (likely edge cases in helpers like chooseCity)

### Risk 3: ANSI conversion breaks formatting
**Mitigation**: Fallback to strip_ansi() if conversion fails, still readable

### Risk 4: Long conversations timeout
**Mitigation**: Add timestamp to conversation state, clear after 15 min

---

## Next Steps

1. **Get maintainer approval** - Show this plan, emphasize zero core changes
2. **Create feature branch** - `feature/telegram-plugin`
3. **Implement PoC** (Phase 1-2, test with `getStatus`)
4. **If PoC works** → Continue with full implementation
5. **Create PR** - With comprehensive testing and documentation

---

## Prompt for Implementation

When ready to implement, use this prompt for a new Claude Code session:

```
Implement Telegram bot plugin for ikabot with COMPLETE separation from core.

Architecture:
- Zero changes to core functions (autoPirate.py, etc)
- Zero changes to command_line.py
- Plugin uses existing predetermined_input + sendToBot()
- Plugin captures stdout and converts ANSI → Telegram Markdown
- Plugin manages multi-step conversations
- Plugin is removable (delete plugins/ folder, ikabot still works)

Implementation phases:
1. Output capture + ANSI formatter (test with getStatus)
2. Telegram polling + basic bot
3. Conversation state manager
4. Menu system + full integration
5. Function metadata for all 25 functions
6. Testing + polish

Key files to create:
- plugins/telegram/bot.py
- plugins/telegram/poller.py
- plugins/telegram/conversation.py
- plugins/telegram/executor.py
- plugins/telegram/formatter.py
- plugins/telegram/menu.py
- plugins/telegram/function_metadata.py
- telegram_bot.py (entry point)

CRITICAL RULES:
1. NO changes to ikabot/function/*.py
2. NO changes to ikabot/command_line.py
3. NO changes to ikabot/helpers/pedirInfo.py
4. NO new dependencies (use existing requests, sendToBot)
5. Test CLI still works after every change

Start with Phase 1: Output capture + ANSI formatter
```

---

**Created**: 2025-11-12
**Status**: Ready for Implementation
**Risk**: LOW (complete separation = zero risk to core)
**Effort**: 16 days
**Dependencies**: ZERO (uses existing infrastructure)
**CONTRIBUTING.md**: ✅ Perfect compliance
