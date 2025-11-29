# Feature #03: CLI Table Auto-Update

**Status**: Proposed Feature
**Priority**: Medium
**Platform**: All platforms (CLI)
**Component**: Command Line Interface (ikabot/command_line.py)
**Type**: Enhancement - User Experience

---

## Summary

Add configurable auto-update capability to the process table displayed at the top of the CLI interface. The table currently only updates when the menu is redrawn, requiring user navigation to see current process statuses.

**Key Requirements**:
1. Must be toggle-able in settings (default: OFF)
2. Must NOT disrupt user navigation (don't switch pages)
3. Must preserve user input (even mid-typing)
4. Should update process status/info in real-time

---

## Current Behavior

### Location
**File**: `ikabot/command_line.py`
**Lines**: 68-113 (in `menu()` function)

### How Table Works Now

**Table Generation** (lines 68-113):
```python
def menu(session, checkUpdate=True):
    # ... banner and other setup ...

    process_list = updateProcessList(session)
    if len(process_list) > 0:
        # Insert table header
        table = process_list.copy()
        table.insert(0, {"pid": "pid", "action": "task", "date": "date", "status": "status"})

        # Calculate column widths dynamically
        max_pid = max([len(row["pid"]) for row in table])
        max_action = max([len(row["action"]) for row in table])
        max_date = max([len(row["date"]) for row in table])

        # Print formatted table
        for i, row in enumerate(table):
            if i == 0:
                print(bcolors.BOLD + ...)  # Header
            else:
                print(...)  # Process rows
```

### Current Update Mechanism

The table is **only** updated when:
1. User enters a menu option and returns to main menu
2. `menu()` function is called
3. User navigates between pages

**No automatic refresh** - table is static between menu() calls.

### What Gets Displayed

Each row shows:
- **PID**: Process ID
- **Task**: Action being performed (e.g., "Pirating", "Donating")
- **Date**: When started
- **Status**: Current status message

### Update Frequency Currently
- **Minimum**: Only on navigation
- **Maximum**: Only on navigation
- **User Action Required**: Yes (must navigate)

---

## Problem

Users cannot see real-time updates to process statuses without:
1. Navigating to another menu and back
2. Selecting an option and returning
3. Manually refreshing somehow

This makes it difficult to:
- Monitor long-running tasks
- See when processes complete
- Track process errors/status changes
- Know current system state

**Impact**:
- **Severity**: LOW (convenience feature)
- **Effect**: Poor user visibility into running processes
- **Workaround**: Navigate away and back to refresh
- **Frequency**: Always (any time user wants current status)

---

## Feature Requirements

### Must Have
1. **Configurable**: Toggle-able setting (default OFF for backwards compatibility)
2. **Non-Disruptive Navigation**: If user is on a different page/menu, don't navigate them away
3. **Preserve Input**: Any text user has typed must survive refresh
4. **Mid-Typing Safety**: Even if user is currently typing, don't lose characters
5. **Performance**: Shouldn't cause noticeable lag or CPU usage

### Nice to Have
6. **Configurable Interval**: Allow user to set refresh rate (e.g., 5s, 10s, 30s)
7. **Visual Indicator**: Show when last updated
8. **Highlight Changes**: Visually indicate rows that changed since last update
9. **Smart Update**: Only redraw if data actually changed

---

## Technical Analysis

### Challenge #1: Terminal Control

**Problem**: Standard `print()` appends to terminal. Can't update in-place without terminal control library.

**Options**:

**A) ANSI Escape Codes (Manual)**
- Pros: No dependencies, lightweight
- Cons: Platform-specific, complex to handle edge cases
- Implementation: Use `\033[A` (cursor up), `\033[K` (clear line)

**B) `curses` library (Standard Library)**
- Pros: Standard library, no install needed, powerful
- Cons: Takes over entire terminal, incompatible with current input model
- Verdict: ❌ Too invasive for this use case

**C) `blessed` library (Third-party)**
- Pros: Cleaner API than curses, allows partial screen updates
- Cons: Requires pip install, adds dependency
- Verdict: ⚠️ Possible but adds dependency

**D) `rich` library (Third-party)**
- Pros: Modern, beautiful, has Live Display feature
- Cons: Requires pip install, heavier dependency
- Verdict: ⚠️ Good for new projects, but adds weight

**E) Simple ANSI approach with line counting**
- Pros: No dependencies, works with current model
- Cons: Needs careful tracking of table height
- Verdict: ✅ **RECOMMENDED** for minimal impact

### Challenge #2: Preserving User Input

**Problem**: When table updates, terminal may interfere with input buffer.

**Current Input Method**:
```python
# Uses read() helper which ultimately uses input()
choice = read(msg=msg, values=options, default="b")
```

**Solution Approaches**:

**A) Check if input() is active**
- Difficult to detect from another thread
- Python's `input()` blocks and doesn't provide hooks

**B) Only update when NOT waiting for input**
- Track state: `is_waiting_for_input` flag
- Only refresh during "safe" moments
- Verdict: ✅ **RECOMMENDED**

**C) Use readline and manual buffer management**
- Pros: Full control over input
- Cons: Major refactor of input system
- Verdict: ❌ Too invasive

### Challenge #3: Threading

**Problem**: Need background thread to periodically refresh table.

**Approach**:
```python
import threading

class TableUpdater:
    def __init__(self, session, refresh_interval=10):
        self.session = session
        self.refresh_interval = refresh_interval
        self.running = False
        self.thread = None
        self.is_input_active = False
        self.last_table_height = 0

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def _update_loop(self):
        while self.running:
            time.sleep(self.refresh_interval)
            if not self.is_input_active:
                self._refresh_table()

    def _refresh_table(self):
        # Get new process list
        # Calculate how many lines to erase (saved height)
        # Move cursor up and clear lines
        # Print new table
        # Update saved height
        pass
```

---

## Proposed Implementation

### Phase 1: Minimal Implementation (RECOMMENDED START)

**Goal**: Add basic auto-update with minimal code changes.

**Changes**:

1. **Add setting to config** (`ikabot/config.py` or session data):
```python
{
    "auto_update_table": False,  # Default OFF
    "table_update_interval": 10,  # Seconds
}
```

2. **Add state tracking to command_line.py**:
```python
# Global state
_is_input_active = False
_table_updater = None

def set_input_active(active):
    global _is_input_active
    _is_input_active = active
```

3. **Create simple updater**:
```python
def start_table_auto_update(session):
    if not session.getSetting("auto_update_table", False):
        return

    def update_loop():
        while True:
            time.sleep(session.getSetting("table_update_interval", 10))
            if not _is_input_active:
                refresh_process_table(session)

    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()

def refresh_process_table(session):
    """Refresh just the process table without full menu redraw"""
    # Save cursor position
    # Get updated process list
    # Calculate lines to clear
    # Move cursor up, clear lines, print new table
    # Restore cursor position
    pass
```

4. **Modify input wrapper to set flag**:
```python
def read(*args, **kwargs):
    set_input_active(True)
    try:
        result = original_read(*args, **kwargs)
        return result
    finally:
        set_input_active(False)
```

### Phase 2: Enhanced Implementation (FUTURE)

**Additional features**:
- Visual diff highlighting (changed rows in different color)
- "Last updated: 5s ago" timestamp
- Smart update (only if data changed)
- Configurable refresh rate in settings menu

---

## Settings Integration

### Where Settings Are Stored

Need to investigate:
- Configuration storage mechanism
- How other settings are managed
- Where to add UI for toggle

### Proposed Setting Location

**Option A**: Session data (per-account setting)
**Option B**: Global config file (applies to all accounts)
**Option C**: Runtime toggle (command line flag)

**Recommendation**: Session data (per-account) since different users may have different preferences.

---

## Edge Cases

### Case 1: Table grows/shrinks
- **Problem**: Number of processes changes, table height changes
- **Solution**: Always track and clear full previous height

### Case 2: Terminal resize
- **Problem**: Terminal width changes, table formatting breaks
- **Solution**: Detect resize, force full redraw

### Case 3: Rapid updates
- **Problem**: Updates faster than display can handle
- **Solution**: Rate limit to reasonable interval (min 5 seconds)

### Case 4: No processes running
- **Problem**: Table disappears, then reappears
- **Solution**: Keep header visible or handle gracefully

### Case 5: User scrolls back
- **Problem**: Update interferes with scrollback viewing
- **Solution**: Only update if terminal is at prompt (hard to detect)

---

## Implementation Risks

### Risk 1: Terminal Compatibility
- **Risk**: ANSI codes may not work on all terminals
- **Mitigation**: Test on Windows CMD, PowerShell, Unix terminals
- **Fallback**: Disable feature if terminal doesn't support ANSI

### Risk 2: Race Conditions
- **Risk**: Update happens during input, corrupts display
- **Mitigation**: Careful state tracking with locks
- **Testing**: Stress test with rapid typing

### Risk 3: Performance Impact
- **Risk**: Background thread consumes resources
- **Mitigation**: Reasonable default interval (10s), daemon thread
- **Monitoring**: Monitor CPU usage during testing

### Risk 4: User Experience
- **Risk**: Updates are distracting rather than helpful
- **Mitigation**: Make it opt-in (default OFF)
- **User Control**: Easy to disable if annoying

---

## Comparison: Other Projects

### Similar Features

**htop / top**: Full-screen auto-updating process viewers
- Use curses for full terminal control
- Different model (dedicated viewer vs menu system)

**tmux status line**: Auto-updating status bar
- Updates specific region without disrupting main content
- Good model for this feature

**Docker CLI**: Shows container status with auto-update
- Uses carriage return and line clearing
- Similar to what we need

---

## Testing Plan

### Manual Testing
- [ ] Enable feature in settings
- [ ] Verify table updates without user action
- [ ] Type text while table updates - verify no character loss
- [ ] Type rapidly during update - verify input preserved
- [ ] Navigate to submenu - verify update doesn't force navigation
- [ ] Disable feature - verify updates stop
- [ ] Multiple processes running (edge case: many rows)
- [ ] Zero processes running (edge case: no rows)
- [ ] Process count changes during runtime

### Platform Testing
- [ ] Linux terminal
- [ ] macOS terminal
- [ ] Windows CMD
- [ ] Windows PowerShell
- [ ] Windows Terminal (new)
- [ ] SSH session (potential lag)

### Performance Testing
- [ ] Monitor CPU usage with feature enabled
- [ ] Test with 1s interval (stress test)
- [ ] Test with 60s interval (slow update)
- [ ] Long-running session (memory leak check)

---

## Alternative Approaches

### Alternative 1: Separate Monitor Window
Instead of updating in-place, open a separate terminal window that shows live process status.

**Pros**: No interference with main menu
**Cons**: Requires window management, OS-specific

### Alternative 2: Web Dashboard
Create a web UI that shows live process status (separate from existing web server).

**Pros**: Better UI possibilities, no terminal issues
**Cons**: Major scope increase, requires browser

### Alternative 3: Status Bar Mode
Add a persistent status bar at top/bottom of terminal (like tmux).

**Pros**: Clean separation, always visible
**Cons**: Requires curses-like library

---

## Recommended Approach

### Start Simple (Phase 1)

1. Add configuration option (default: OFF)
2. Implement basic ANSI-based refresh
3. Add input-active state tracking
4. Test thoroughly on major platforms

### Enhance Later (Phase 2)

5. Add visual enhancements (color changes, timestamps)
6. Add smart update (only if changed)
7. Add user-configurable interval
8. Add setting toggle to main menu

---

## Related Files

- **Primary**: `ikabot/command_line.py:68-113` (table display)
- **Settings**: Need to locate configuration storage
- **Process Management**: `ikabot/command_line.py:54-64` (`updateProcessList()`)
- **Input Handling**: `ikabot/helpers/gui.py` (likely location of `read()` function)

---

## Open Questions

1. **Where are settings stored?** Need to investigate config system
2. **What terminals are primary targets?** Windows? Linux? Both?
3. **Default interval?** 10 seconds? User configurable?
4. **Always show header?** Even when no processes?
5. **Visual indicators?** Colors for status changes?

---

## Timeline

- **Proposed**: 2025-11-10
- **Analysis Complete**: 2025-11-10
- **Implementation**: TBD
- **Testing**: TBD
- **Release**: TBD

---

## Notes

- Feature should be **opt-in** to avoid surprising existing users
- Terminal compatibility is critical - must degrade gracefully
- User input preservation is **non-negotiable** requirement
- Performance impact must be minimal (background thread, reasonable interval)
- This is a quality-of-life feature, not critical functionality

---

## User Feedback

User specifically requested:
> "can there be a feature (that must be toggled on in settings - that will enable autoupdate of the table, i think it was called something "Sandox" it *must not* disrupt user actions ie if 1)user on different page should not take it from them to updated page, 2) if user has something typed in -- (even while on the same page) the typed in should survive refresh (to a degree if it caughts user mid typing)"

**Key Requirements from User**:
- ✅ Toggle in settings
- ✅ Don't disrupt navigation
- ✅ Preserve typed input (even mid-typing)
