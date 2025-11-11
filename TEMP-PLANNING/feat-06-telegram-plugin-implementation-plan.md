# Feature #06: Telegram Plugin Implementation Plan (Using Existing Infrastructure)

**Status**: Implementation Plan Ready
**Priority**: HIGH
**Difficulty**: **3-4/10** (Much easier than expected!)
**Component**: New Plugin Module
**Type**: Major Feature - Telegram Bot Interface

---

## 🎉 MAJOR DISCOVERY: Existing Infrastructure!

Ikabot **already has Telegram support infrastructure!** This dramatically reduces implementation complexity.

### What Already Exists

#### 1. Telegram Communication (`ikabot/helpers/botComm.py`)

**Already implemented functions**:
- ✅ `sendToBot(session, msg)` - Send messages to Telegram (line 34-79)
- ✅ `getUserResponse(session)` - Get messages from user (line 105-151)
- ✅ `updateTelegramData(session)` - Setup bot token & chat ID (line 186-282)
- ✅ `telegramDataIsValid(session)` - Check if configured (line 82-102)

**Uses direct Telegram Bot API**:
```python
# From botComm.py:61-66
return get(
    "https://api.telegram.org/bot{}/sendMessage".format(
        telegram_data["botToken"]
    ),
    params={"chat_id": telegram_data["chatId"], "text": msg},
)
```

**No external dependency needed!** Uses existing `requests` library.

#### 2. Session Data Storage

**Already stores Telegram config** (`session.py`):
```python
sessionData["shared"]["telegram"] = {
    "botToken": "...",
    "chatId": "..."
}
```

#### 3. Predetermined Input Mechanism (`config.py:87`)

**Already has state automation**:
```python
predetermined_input = []  # Global list for automated inputs
```

**Already used in CLI**:
```python
# command_line.py:289
args=(session, event, sys.stdin.fileno(), config.predetermined_input)

# pedirInfo.py:62-63
if len(config.predetermined_input) != 0:
    return config.predetermined_input.pop(0)
```

**This is exactly what we need for Telegram state management!**

---

## Revised Difficulty Assessment

### Original Estimate: 6-7/10
### Revised Estimate: **3-4/10**

| Aspect | Original | Revised | Why Easier |
|--------|----------|---------|------------|
| Telegram API | 3/10 | **1/10** | Already implemented! |
| Dependency management | 5/10 | **0/10** | No new dependencies! |
| State management | 8/10 | **4/10** | predetermined_input already exists! |
| Input abstraction | 5/10 | **3/10** | Just need to populate predetermined_input |
| Multi-user support | 6/10 | **5/10** | Need per-user sessions (still complex) |
| Integration | 7/10 | **4/10** | Can be plugin, no core changes |

**Average**: 6.3/10 → **3.0/10**

---

## No python-telegram-bot Needed!

### Why It's Not Needed

1. **Ikabot uses direct HTTP API**
   - `requests.get()` to Telegram API endpoints
   - No polling loop (uses getUpdates when needed)
   - Simpler, more lightweight

2. **CONTRIBUTING.md Compliant**
   - ✅ No new dependencies
   - ✅ Lightweight design
   - ✅ Uses existing `requests` library

3. **Current Implementation Pattern**
   - Notification-only (sends alerts to user)
   - Can be extended to two-way communication

### Comparison

**python-telegram-bot approach**:
```python
# Requires new dependency
from telegram import Update
from telegram.ext import Application, CommandHandler

app = Application.builder().token("TOKEN").build()
app.add_handler(CommandHandler("start", start_handler))
app.run_polling()  # Runs forever
```

**Existing Ikabot approach**:
```python
# No new dependencies!
from requests import get

# Send message
get("https://api.telegram.org/bot{TOKEN}/sendMessage",
    params={"chat_id": chatId, "text": msg})

# Get messages
updates = get("https://api.telegram.org/bot{TOKEN}/getUpdates").json()
```

✅ **Winner**: Existing approach (lightweight, no dependencies)

---

## Architecture: Plugin-Based Design

### 1. Plugin Structure

```
ikabot/
├── plugins/
│   ├── __init__.py
│   └── telegram/
│       ├── __init__.py
│       ├── telegram_interface.py    # Main plugin entry
│       ├── input_handler.py         # Telegram input adapter
│       ├── conversation.py          # Conversation state manager
│       └── keyboards.py             # Inline keyboard builder
```

### 2. Core Abstraction Layer

**Minimal changes to existing code**:

#### Option A: Zero Changes (Recommended for 1 user/1 bot)

**Don't change existing functions at all!**

Instead, create a **wrapper** that:
1. Receives Telegram messages
2. Populates `predetermined_input` with user's answers
3. Calls existing CLI functions
4. Intercepts `print()` output and sends to Telegram

**Example**:
```python
# plugins/telegram/telegram_interface.py

class TelegramInterface:
    def __init__(self, session):
        self.session = session
        self.conversation_state = {}

    def run_function_via_telegram(self, function_name, user_message):
        """Run any CLI function via Telegram"""

        # Parse user input based on conversation state
        if user_message.isdigit():
            config.predetermined_input.append(int(user_message))
        else:
            config.predetermined_input.append(user_message)

        # Capture print() output
        captured_output = []
        original_print = print
        def telegram_print(*args, **kwargs):
            captured_output.append(' '.join(str(arg) for arg in args))

        # Run function (temporarily redirect print)
        import builtins
        builtins.print = telegram_print
        try:
            # Call the actual CLI function
            # It will read from predetermined_input instead of terminal!
            result = function_name(self.session, event, stdin_fd, config.predetermined_input)
        finally:
            builtins.print = original_print

        # Send captured output to Telegram
        for line in captured_output:
            sendToBot(self.session, line)
```

**Pros**:
- ✅ ZERO changes to existing functions
- ✅ Reuses ALL existing code
- ✅ predetermined_input already handles state!
- ✅ Perfect for 1 user/1 bot architecture

**Cons**:
- ⚠️ Hacky (redirecting print)
- ⚠️ Hard to control output formatting
- ⚠️ Function still expects terminal context

#### Option B: Minimal Abstraction Layer

**Small changes to functions** (optional input_handler):

```python
# ikabot/helpers/input_abstraction.py

class InputHandler:
    """Base class for input handling"""
    def read(self, **kwargs):
        raise NotImplementedError

    def print(self, text):
        raise NotImplementedError

    def banner(self):
        raise NotImplementedError

class CLIInputHandler(InputHandler):
    """CLI mode - uses existing functions"""
    def read(self, **kwargs):
        from ikabot.helpers.pedirInfo import read
        return read(**kwargs)

    def print(self, text):
        print(text)

    def banner(self):
        from ikabot.helpers.gui import banner
        banner()

class TelegramInputHandler(InputHandler):
    """Telegram mode - sends messages, uses predetermined_input"""
    def __init__(self, session, chat_id):
        self.session = session
        self.chat_id = chat_id

    def read(self, **kwargs):
        # Check predetermined_input first (from Telegram messages)
        if len(config.predetermined_input) > 0:
            return config.predetermined_input.pop(0)
        else:
            # Need more input from user
            # Send question to Telegram
            msg = kwargs.get('msg', 'Enter value:')
            sendToBot(self.session, msg)
            # Raise exception to pause execution
            raise NeedUserInputException()

    def print(self, text):
        sendToBot(self.session, text)

    def banner(self):
        pass  # Skip banner on Telegram
```

**Modify functions** (add optional parameter):
```python
def autoPirate(session, event, stdin_fd, predetermined_input, input_handler=None):
    if input_handler is None:
        input_handler = CLIInputHandler()  # Default to CLI

    input_handler.banner()
    input_handler.print("⚠️ WARNING ⚠️")

    pirateCount = input_handler.read(min=1, digit=True)
    schedule = input_handler.read(values=["y", "Y", "n", "N", ""])
    # ... rest unchanged
```

**Pros**:
- ✅ Clean abstraction
- ✅ Easy to control output
- ✅ Better for future expansion

**Cons**:
- ❌ Need to modify all ~25 functions
- ❌ More invasive changes

### Recommendation for 1 User/1 Bot

**Use Option A (Zero Changes)** because:
1. No changes to existing code (CONTRIBUTING.md compliant)
2. predetermined_input is perfect for single user
3. Faster to implement
4. Less risky (no breaking CLI)

---

## Implementation Plan: Plugin-Based (Zero Changes Approach)

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│               User on Telegram                   │
└───────────────────┬─────────────────────────────┘
                    │ Messages
                    ↓
┌─────────────────────────────────────────────────┐
│        Telegram Bot (Polling Thread)            │
│  - Polls getUpdates every 2 seconds             │
│  - Receives messages from user                  │
└───────────────────┬─────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────┐
│         Conversation State Manager              │
│  - Tracks which function user is in             │
│  - Stores partial answers (step tracking)       │
│  - Uses predetermined_input for automation      │
└───────────────────┬─────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────┐
│           Function Executor                     │
│  - Populates predetermined_input                │
│  - Calls existing CLI functions                 │
│  - Captures output (print interception)         │
└───────────────────┬─────────────────────────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────┐
│       Existing CLI Functions (Unchanged!)       │
│  - autoPirate(), sendResources(), etc.          │
│  - Read from predetermined_input                │
│  - Print to stdout (intercepted)                │
└───────────────────┬─────────────────────────────┘
                    │ Output
                    ↓
┌─────────────────────────────────────────────────┐
│        Send to Telegram via sendToBot()         │
└─────────────────────────────────────────────────┘
```

### Phase 1: Telegram Poller (2-3 days)

**Create**: `ikabot/plugins/telegram/poller.py`

**Purpose**: Background thread that polls Telegram for messages

**Code**:
```python
import threading
import time
from requests import get
from ikabot.helpers.botComm import sendToBot

class TelegramPoller:
    def __init__(self, session):
        self.session = session
        self.running = False
        self.thread = None
        self.last_update_id = 0
        self.message_handlers = []

    def start(self):
        """Start polling thread"""
        self.running = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop polling"""
        self.running = False

    def add_handler(self, handler_func):
        """Add message handler function"""
        self.message_handlers.append(handler_func)

    def _poll_loop(self):
        """Main polling loop"""
        sessionData = self.session.getSessionData()
        telegram_data = sessionData["shared"]["telegram"]
        bot_token = telegram_data["botToken"]

        while self.running:
            try:
                # Poll for updates
                updates = get(
                    f"https://api.telegram.org/bot{bot_token}/getUpdates",
                    params={
                        "offset": self.last_update_id + 1,
                        "timeout": 30  # Long polling
                    }
                ).json()

                if updates.get("ok") and updates.get("result"):
                    for update in updates["result"]:
                        self.last_update_id = update["update_id"]

                        # Call message handlers
                        for handler in self.message_handlers:
                            handler(update)

            except Exception as e:
                print(f"Telegram polling error: {e}")
                time.sleep(5)  # Wait before retry

            time.sleep(2)  # Poll every 2 seconds
```

**Effort**: 2-3 days
**Dependencies**: None (uses existing requests)

---

### Phase 2: Conversation State Manager (3-4 days)

**Create**: `ikabot/plugins/telegram/conversation.py`

**Purpose**: Track where user is in multi-step functions

**Code**:
```python
class ConversationState:
    """Tracks user's position in conversation"""

    def __init__(self):
        self.states = {}  # chat_id -> state_dict

    def get_state(self, chat_id):
        """Get user's current state"""
        return self.states.get(chat_id, {
            "function": None,
            "step": 0,
            "data": {},
            "waiting_for": None
        })

    def set_state(self, chat_id, function_name, step, waiting_for):
        """Update user's state"""
        if chat_id not in self.states:
            self.states[chat_id] = {}

        self.states[chat_id].update({
            "function": function_name,
            "step": step,
            "waiting_for": waiting_for
        })

    def save_answer(self, chat_id, answer):
        """Save user's answer to current step"""
        state = self.get_state(chat_id)
        step_name = state["waiting_for"]
        state["data"][step_name] = answer
        self.states[chat_id] = state

    def clear_state(self, chat_id):
        """Clear user's conversation (done or cancelled)"""
        if chat_id in self.states:
            del self.states[chat_id]

    def populate_predetermined_input(self, chat_id):
        """Fill predetermined_input with saved answers"""
        state = self.get_state(chat_id)
        config.predetermined_input.clear()

        # Add all saved answers in order
        for step_name in sorted(state["data"].keys()):
            config.predetermined_input.append(state["data"][step_name])

    def is_in_conversation(self, chat_id):
        """Check if user is in active conversation"""
        state = self.get_state(chat_id)
        return state["function"] is not None
```

**Effort**: 3-4 days
**Dependencies**: None

---

### Phase 3: Function Executor (4-5 days)

**Create**: `ikabot/plugins/telegram/executor.py`

**Purpose**: Execute CLI functions via Telegram

**Code**:
```python
import io
import sys
import contextlib
import multiprocessing
from ikabot import config

class FunctionExecutor:
    """Execute CLI functions via Telegram"""

    def __init__(self, session, conversation_state):
        self.session = session
        self.conversation_state = conversation_state

    def execute_function(self, chat_id, function_ref, user_input=None):
        """
        Execute a function with Telegram as interface

        Parameters:
        - chat_id: Telegram chat ID
        - function_ref: Reference to CLI function (e.g., autoPirate)
        - user_input: User's latest input (if continuing conversation)
        """

        # Get conversation state
        state = self.conversation_state.get_state(chat_id)

        # If user provided input, save it
        if user_input:
            self.conversation_state.save_answer(chat_id, user_input)

        # Populate predetermined_input with all saved answers
        self.conversation_state.populate_predetermined_input(chat_id)

        # Capture stdout to send to Telegram
        captured_output = io.StringIO()

        try:
            with contextlib.redirect_stdout(captured_output):
                # Create event for function completion
                event = multiprocessing.Event()

                # Try to execute function
                # It will read from predetermined_input
                try:
                    function_ref(
                        self.session,
                        event,
                        sys.stdin.fileno(),
                        config.predetermined_input
                    )

                    # Function completed!
                    self.conversation_state.clear_state(chat_id)
                    sendToBot(self.session, "✅ Task started successfully!")

                except IndexError:
                    # predetermined_input ran out - need more from user
                    # Function is waiting for next input
                    output = captured_output.getvalue()

                    # Send last question to Telegram
                    lines = output.strip().split('\n')
                    last_question = lines[-1] if lines else "Please enter value:"

                    sendToBot(self.session, last_question)

                    # Update state (increment step, note what we're waiting for)
                    state = self.conversation_state.get_state(chat_id)
                    self.conversation_state.set_state(
                        chat_id,
                        function_ref.__name__,
                        state["step"] + 1,
                        f"step_{state['step'] + 1}"
                    )

        except Exception as e:
            # Error occurred
            sendToBot(self.session, f"❌ Error: {str(e)}")
            self.conversation_state.clear_state(chat_id)
```

**Effort**: 4-5 days (most complex part)
**Challenges**:
- Print interception
- Detecting when function needs more input
- Error handling

---

### Phase 4: Menu System (2-3 days)

**Create**: `ikabot/plugins/telegram/menu.py`

**Purpose**: Telegram inline keyboards for menu navigation

**Code**:
```python
from ikabot.helpers.botComm import sendToBot
from requests import get

class TelegramMenu:
    """Telegram menu system using inline keyboards"""

    def __init__(self, session):
        self.session = session

    def send_main_menu(self, chat_id):
        """Send main menu as inline keyboard"""

        sessionData = self.session.getSessionData()
        telegram_data = sessionData["shared"]["telegram"]
        bot_token = telegram_data["botToken"]

        # Build inline keyboard (max 8 buttons per message)
        keyboard = {
            "inline_keyboard": [
                [{"text": "📋 Construction List", "callback_data": "menu_1"}],
                [{"text": "📦 Send Resources", "callback_data": "menu_2"}],
                [{"text": "⚖️ Distribute Resources", "callback_data": "menu_3"}],
                [{"text": "📊 Account Status", "callback_data": "menu_4"}],
                [{"text": "⚔️ Military", "callback_data": "menu_12"}],
                [{"text": "🏴‍☠️ Auto-Pirate", "callback_data": "menu_17"}],
                [{"text": "⚙️ More...", "callback_data": "menu_more"}]
            ]
        }

        get(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            params={
                "chat_id": chat_id,
                "text": "🤖 *Ikabot Menu*\n\nChoose an action:",
                "parse_mode": "Markdown",
                "reply_markup": json.dumps(keyboard)
            }
        )

    def send_submenu(self, chat_id, submenu_id):
        """Send submenu (e.g., Military options)"""
        # Similar to main menu but with submenu options
        pass
```

**Effort**: 2-3 days
**Dependencies**: None

---

### Phase 5: Main Plugin Entry (2 days)

**Create**: `ikabot/plugins/telegram/__init__.py`

**Purpose**: Plugin entry point and coordinator

**Code**:
```python
from ikabot.plugins.telegram.poller import TelegramPoller
from ikabot.plugins.telegram.conversation import ConversationState
from ikabot.plugins.telegram.executor import FunctionExecutor
from ikabot.plugins.telegram.menu import TelegramMenu

# Map menu options to functions
from ikabot.command_line import menu_actions

class TelegramPlugin:
    """Main Telegram plugin coordinator"""

    def __init__(self, session):
        self.session = session
        self.conversation_state = ConversationState()
        self.executor = FunctionExecutor(session, self.conversation_state)
        self.menu = TelegramMenu(session)
        self.poller = TelegramPoller(session)

    def start(self):
        """Start Telegram interface"""
        # Register message handler
        self.poller.add_handler(self.handle_message)

        # Start polling
        self.poller.start()

        print("✅ Telegram plugin started")
        sendToBot(self.session, "🤖 Ikabot Telegram interface is ready!")
        self.menu.send_main_menu(self.get_chat_id())

    def get_chat_id(self):
        """Get user's chat ID from session"""
        sessionData = self.session.getSessionData()
        return int(sessionData["shared"]["telegram"]["chatId"])

    def handle_message(self, update):
        """Handle incoming Telegram message"""
        if "callback_query" in update:
            # Button click
            self.handle_button_click(update["callback_query"])
        elif "message" in update:
            # Text message
            self.handle_text_message(update["message"])

    def handle_button_click(self, callback_query):
        """Handle inline keyboard button click"""
        chat_id = callback_query["from"]["id"]
        data = callback_query["data"]

        if data.startswith("menu_"):
            # Menu option selected
            option = int(data.split("_")[1])
            function = menu_actions.get(option)

            if function:
                # Start function execution
                self.executor.execute_function(chat_id, function)

    def handle_text_message(self, message):
        """Handle text message from user"""
        chat_id = message["chat"]["id"]
        text = message["text"]

        # Check if user is in active conversation
        if self.conversation_state.is_in_conversation(chat_id):
            # Continue conversation with user's answer
            state = self.conversation_state.get_state(chat_id)
            function_name = state["function"]
            function = menu_actions.get(function_name)

            self.executor.execute_function(chat_id, function, user_input=text)
        else:
            # Not in conversation - show menu
            if text == "/start" or text == "/menu":
                self.menu.send_main_menu(chat_id)
            else:
                sendToBot(self.session, "Use /menu to see options")

# Plugin entry point
def start_telegram_plugin(session):
    """Start the Telegram plugin"""
    plugin = TelegramPlugin(session)
    plugin.start()
    return plugin
```

**Effort**: 2 days
**Dependencies**: None

---

### Phase 6: CLI Integration (1 day)

**Modify**: `ikabot/command_line.py` (minimal addition)

**Add option to start Telegram interface**:

```python
# Add to menu (option 24)
print("(24) Start Telegram Interface")

menu_actions[24] = lambda sess, evt, fd, inp: start_telegram_plugin(sess)
```

**Or** create standalone script:

**Create**: `telegram_bot.py` (root of project)

```python
#!/usr/bin/env python3
"""
Standalone Telegram Bot Interface for Ikabot
Runs independently of CLI
"""

from ikabot.web.session import Session
from ikabot.plugins.telegram import start_telegram_plugin

def main():
    print("Starting Ikabot Telegram Bot...")
    session = Session()

    if not session.logged:
        print("❌ Failed to login")
        return

    # Start plugin
    plugin = start_telegram_plugin(session)

    # Keep running
    print("Bot running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping bot...")
        plugin.poller.stop()

if __name__ == "__main__":
    main()
```

**Usage**:
```bash
python telegram_bot.py
```

**Effort**: 1 day

---

## Total Effort Estimate (Zero Changes Approach)

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| 1. Telegram Poller | 2-3 days | None |
| 2. Conversation State | 3-4 days | None |
| 3. Function Executor | 4-5 days | Phase 2 |
| 4. Menu System | 2-3 days | Phase 1 |
| 5. Plugin Entry | 2 days | All above |
| 6. CLI Integration | 1 day | Phase 5 |
| **TOTAL** | **14-18 days** | - |

**For experienced developer**: 2-3 weeks
**For part-time contributor**: 4-6 weeks
**With testing & refinement**: 3-4 weeks total

---

## What Can Be Reused (Assessment)

### ✅ Can Be Reused Completely

1. **Telegram Communication** (`botComm.py`)
   - sendToBot() - ✅ Perfect, no changes needed
   - getUserResponse() - ✅ Works, but polling is better
   - updateTelegramData() - ✅ Perfect for setup
   - All session storage - ✅ Perfect

2. **predetermined_input Mechanism** (`config.py`, `pedirInfo.py`)
   - ✅ EXACTLY what we need for state!
   - ✅ Already handles automation
   - ✅ No changes needed

3. **All CLI Functions**
   - ✅ autoPirate(), sendResources(), etc.
   - ✅ Can be called unchanged
   - ✅ Already read from predetermined_input

4. **Session Management**
   - ✅ One session per bot (perfect for 1 user/1 bot)
   - ✅ Login/logout already handled
   - ✅ Session data storage ready

### ⚠️ Needs Slight Adaptation

5. **Process Management**
   - Current: multiprocessing.Process
   - Telegram: Still works, but monitoring different
   - Solution: Keep it, add Telegram status updates

6. **Output Display**
   - Current: print() to terminal
   - Telegram: Need to intercept and send via sendToBot()
   - Solution: Context manager for stdout redirection

### ❌ Cannot Be Reused (Need New)

7. **Menu Navigation**
   - Current: Number selection + Enter
   - Telegram: Inline keyboard buttons
   - Solution: New menu.py (Phase 4)

8. **Polling Loop**
   - Current: None (CLI is synchronous)
   - Telegram: Need background thread
   - Solution: New poller.py (Phase 1)

9. **Conversation State Tracking**
   - Current: Call stack (function blocks until done)
   - Telegram: Must save between messages
   - Solution: New conversation.py (Phase 2)

---

## Architectural Decisions

### Decision 1: Plugin vs Core Integration

**Choice**: **Plugin Architecture**

**Rationale**:
- ✅ No changes to core code
- ✅ Optional feature (doesn't bloat core)
- ✅ Can be disabled/removed easily
- ✅ Follows CONTRIBUTING.md (lightweight)

### Decision 2: Polling vs Webhooks

**Choice**: **Polling (getUpdates)**

**Rationale**:
- ✅ Simpler to implement
- ✅ No need for public URL/SSL certificates
- ✅ Works behind firewalls
- ✅ Matches existing getUserResponse() pattern
- ❌ Slightly less efficient (but fine for 1 user)

### Decision 3: Zero Changes vs Abstraction Layer

**Choice**: **Zero Changes (for 1 user/1 bot)**

**Rationale**:
- ✅ Fastest to implement
- ✅ No risk of breaking CLI
- ✅ predetermined_input is sufficient
- ✅ CONTRIBUTING.md compliant
- ⚠️ Can always add abstraction later if needed

### Decision 4: Separate Process vs Thread

**Choice**: **Thread (for polling)**

**Rationale**:
- ✅ Simpler inter-thread communication
- ✅ Share same Session object
- ✅ Don't need multiprocessing complexity
- ❌ GIL limitations (but I/O bound, not CPU bound)

---

## 1 Person / 1 Bot / 1 Ikariam - Optimizations

Since we have these constraints, we can simplify:

### Optimization 1: Single Session

**No multi-user logic needed**:
```python
# One global session
telegram_session = Session()

# No need for session-per-user dict
# No need for authentication per message
```

### Optimization 2: Single Conversation

**No concurrent conversation tracking**:
```python
# Just one conversation state
current_function = None
current_step = 0
accumulated_inputs = []

# No need for chat_id -> state dict
```

### Optimization 3: Simpler State Management

**predetermined_input is perfect**:
```python
# User sends: "5"
config.predetermined_input.append(5)

# User sends: "y"
config.predetermined_input.append("y")

# Function runs and consumes from predetermined_input
# Exactly like CLI with command-line arguments!
```

### Optimization 4: No Session Persistence Needed

**Bot restarts = fresh start**:
- ✅ No need to save state to disk
- ✅ No need to recover conversations
- ✅ User just starts over (acceptable for 1 user)

---

## CONTRIBUTING.md Compliance Check

### 1. Lightweight Design ✅

**Requirement**: "Avoid changes that compromise the project's lightweight and efficient nature"

**Our Approach**:
- ✅ Plugin architecture (optional)
- ✅ No core code changes
- ✅ Can be disabled entirely
- ✅ Minimal overhead (polling thread only)

### 2. Dependency Management ✅

**Requirement**: "Introduce new dependencies only if crucial"

**Our Approach**:
- ✅ **ZERO new dependencies!**
- ✅ Uses existing `requests` library
- ✅ Uses existing Telegram infrastructure

### 3. Python Version ✅

**Requirement**: "Utilize latest Python versions"

**Our Approach**:
- ✅ Uses standard library (threading, io, contextlib)
- ✅ Compatible with Python 3.8+
- ✅ No legacy code

### 4. Code Formatting ✅

**Requirement**: "Use Black formatter"

**Our Approach**:
- ✅ Will format all new code with Black
- ✅ Follow existing code style

---

## Risk Assessment (Revised)

### High Risks → Now Low Risks!

1. **Dependency rejection**
   - Was: MEDIUM probability
   - Now: **ZERO risk** (no new dependencies!)

2. **Breaking CLI**
   - Was: HIGH severity
   - Now: **ZERO risk** (no changes to CLI!)

3. **State management bugs**
   - Was: HIGH complexity
   - Now: **LOW** (predetermined_input already works!)

### Remaining Medium Risks

4. **Output interception reliability**
   - Severity: MEDIUM
   - Probability: MEDIUM
   - Mitigation: Thorough testing, fallback to simple sendToBot()

5. **Detecting when function needs input**
   - Severity: MEDIUM
   - Probability: HIGH
   - Mitigation: Try-except around function calls, detect IndexError

### Low Risks

6. **Telegram API changes**
   - Severity: LOW
   - Probability: LOW
   - Mitigation: Telegram Bot API is very stable

---

## Implementation Strategy

### Week 1: Foundation
- Days 1-2: Phase 1 (Poller)
- Days 3-4: Phase 2 (Conversation State)
- Day 5: Testing & integration

### Week 2: Execution & Menu
- Days 1-3: Phase 3 (Function Executor)
- Days 4-5: Phase 4 (Menu System)

### Week 3: Integration & Polish
- Days 1-2: Phase 5 (Plugin Entry)
- Day 3: Phase 6 (CLI Integration)
- Days 4-5: Testing & bug fixes

---

## Testing Plan

### Unit Tests

**Test predetermined_input population**:
```python
def test_conversation_state_populates_predetermined_input():
    state = ConversationState()
    state.save_answer(chat_id=123, answer="5")
    state.save_answer(chat_id=123, answer="y")
    state.populate_predetermined_input(chat_id=123)

    assert config.predetermined_input == ["5", "y"]
```

**Test function execution**:
```python
def test_execute_simple_function():
    # Mock simple function
    def test_func(session, event, stdin_fd, predetermined_input):
        val = predetermined_input.pop(0)
        return val

    config.predetermined_input = [42]
    executor = FunctionExecutor(session, conversation_state)
    result = executor.execute_function(chat_id=123, function_ref=test_func)

    assert result == 42
```

### Integration Tests

**Test autoPirate flow**:
1. User clicks "Auto-Pirate" button
2. Bot asks "How many missions?"
3. User sends "5"
4. Bot asks "Schedule?"
5. User sends "n"
6. Bot asks "Which mission?"
7. User sends "3"
8. Bot confirms "✅ Task started!"

**Test with predetermined_input**:
```python
def test_autopirate_full_flow():
    config.predetermined_input = [5, "n", 3]

    # Execute autoPirate
    executor.execute_function(chat_id=123, function_ref=autoPirate)

    # Should complete without errors
    assert conversation_state.is_in_conversation(chat_id=123) == False
```

### Manual Testing

- [ ] Send /start command
- [ ] Click each menu button
- [ ] Complete simple function (getStatus)
- [ ] Complete complex function (autoPirate with schedule)
- [ ] Test cancel mid-flow (Ctrl+C equivalent)
- [ ] Test invalid inputs
- [ ] Test long-running tasks
- [ ] Test multiple back-to-back functions

---

## Success Criteria

### Must Have (MVP)
- [ ] Telegram poller receives messages
- [ ] Main menu displays with inline keyboard
- [ ] Can execute getStatus via Telegram
- [ ] Can execute autoPirate via Telegram (full flow)
- [ ] predetermined_input mechanism works
- [ ] Output sent to Telegram
- [ ] CLI completely unchanged and working

### Should Have (v1.0)
- [ ] All functions accessible via menu
- [ ] Submenus work (Military, Marketplace, etc.)
- [ ] Error handling and user feedback
- [ ] /cancel command to abort conversation
- [ ] /status command to see running tasks
- [ ] Basic logging

### Nice to Have (Future)
- [ ] Session persistence (survive bot restart)
- [ ] Multi-user support (if needed later)
- [ ] Abstraction layer (if expanding beyond Telegram)
- [ ] Webhooks instead of polling (efficiency)

---

## Migration Path (If Multi-User Needed Later)

If we later need to support multiple users:

### Step 1: Add User Session Map
```python
user_sessions = {}  # chat_id -> Session

def get_session(chat_id):
    if chat_id not in user_sessions:
        user_sessions[chat_id] = Session()
    return user_sessions[chat_id]
```

### Step 2: Add Per-User Conversation State
```python
# Already designed for this!
conversation_state.states[chat_id]  # Already separated by chat_id
```

### Step 3: Add Per-User predetermined_input
```python
# Instead of global config.predetermined_input
user_inputs = {}  # chat_id -> list

# Pass to functions:
function(session, event, stdin_fd, user_inputs[chat_id])
```

**Estimated Effort**: 2-3 days to add multi-user support

---

## Comparison: Original Plan vs Revised Plan

| Aspect | Original (feat-05) | Revised (feat-06) | Change |
|--------|-------------------|-------------------|--------|
| **Difficulty** | 6-7/10 | **3-4/10** | ⬇️ 50% easier |
| **Effort** | 14-21 days | **14-18 days** | ⬇️ Similar, but safer |
| **Dependencies** | python-telegram-bot | **None!** | ✅ Major win |
| **Core changes** | ~25 functions | **Zero!** | ✅ Huge win |
| **Risk** | Medium-High | **Low** | ✅ Much safer |
| **CONTRIBUTING** | Questionable | **Perfect** | ✅ Compliant |

---

## Recommendation

### Should We Proceed?
**Strong YES!**

### Why?
1. ✅ **No new dependencies** (CONTRIBUTING.md compliant)
2. ✅ **Zero core changes** (no risk to CLI)
3. ✅ **Existing infrastructure** (predetermined_input, botComm.py)
4. ✅ **Much easier than expected** (3-4/10 difficulty)
5. ✅ **High user value** (mobile access)
6. ✅ **Plugin architecture** (optional, removable)

### Start With
**Phase 1: Proof of Concept (1 week)**
- Implement poller
- Implement basic conversation state
- Test with ONE simple function (getStatus)
- Validate approach works

**If PoC succeeds** → Continue with full implementation
**If PoC has issues** → Re-evaluate approach

---

## Next Steps

1. **Get maintainer approval**
   - Present this plan
   - Show CONTRIBUTING.md compliance
   - Demonstrate no new dependencies

2. **Create PoC branch**
   - `feature/telegram-plugin-poc`
   - Implement Phase 1 only
   - Test with getStatus function

3. **Review PoC**
   - Does it work?
   - Is print interception reliable?
   - Is predetermined_input sufficient?

4. **If approved** → Full implementation
   - Follow phase plan (Weeks 1-3)
   - Test each phase thoroughly
   - Document as you go

---

## Conclusion

The discovery that Ikabot **already has Telegram infrastructure** changes everything:

- **No python-telegram-bot needed** → CONTRIBUTING.md compliant ✅
- **predetermined_input exists** → State management solved ✅
- **sendToBot() exists** → Communication solved ✅
- **Plugin architecture** → Zero core changes ✅

**Revised Assessment**:
- **Difficulty**: 3-4/10 (was 6-7/10)
- **Effort**: 2-3 weeks (was 3-6 weeks)
- **Risk**: Low (was Medium-High)
- **Recommendation**: **Proceed immediately!**

This is now a **low-risk, high-value feature** that perfectly aligns with the project's lightweight philosophy.

---

**Created**: 2025-11-10
**Analysis Complete**: Yes
**Recommendation**: **PROCEED WITH PROOF OF CONCEPT**
**Estimated Timeline**: 1 week for PoC, 2-3 weeks for full implementation
**Risk Level**: Low (minimal changes, no dependencies)
**CONTRIBUTING.md Compliance**: ✅ Perfect
