# Feature #09: Alert Debug Logging for Attack Classification

**Status**: Design Complete
**Priority**: HIGH (needed for issue-04 fix)
**Difficulty**: 1/10 (simple logging addition)
**Component**: alertAttacks.py
**Type**: Debug Feature - Data Discovery

---

## Purpose

Add persistent debug logging to capture full military movement data structure when alerts trigger. This will reveal:
1. What fields are available in the API response
2. How to reliably detect pirate attacks vs player attacks
3. What other attack types exist

**Why needed**: Current code doesn't distinguish attack types, causing user confusion.

---

## Current Detection Mechanic

### What alertAttacks.py Currently Does

**File**: `ikabot/function/alertAttacks.py:124-126`

```python
for militaryMovement in [
    mov for mov in militaryMovements if mov["isHostile"]
]:
```

**That's it!** Only one filter: `isHostile == true`

**No other detection:**
- ❌ Doesn't check if pirate vs player
- ❌ Doesn't check attack type (raid/pillage/occupy)
- ❌ Doesn't check if own movement vs incoming
- ❌ No logging of available data fields

**Result**: Everything marked `isHostile` triggers alert with same generic message.

---

## What Data We Currently Extract

**Lines 134-139:**

```python
missionText = militaryMovement["event"]["missionText"]  # "Přepadení (probíhá)"
origin = militaryMovement["origin"]                     # {...}
target = militaryMovement["target"]                     # {...}
amountTroops = militaryMovement["army"]["amount"]       # 0
amountFleets = militaryMovement["fleet"]["amount"]      # 0
timeLeft = int(militaryMovement["eventTime"]) - timeNow # seconds
```

**From origin object:**
```python
origin["name"]        # "Hr4fnsfj0rdur"
origin["avatarName"]  # "_K4_"
```

**What we DON'T check:**
- `militaryMovement["event"]` - other fields?
- `militaryMovement["origin"]` - full structure?
- `militaryMovement["target"]` - full structure?
- `militaryMovement` top level - other fields?
- Any `isPirate`, `missionType`, `avatarId`, etc.?

---

## Proposed Debug Feature

### Design: Persistent File Logging

Write full movement data to file when alert triggers, for later analysis.

**Log location**: `~/.ikabot_alert_debug.log`

**Format**: JSON lines (one movement per line)

**Contents**: Full militaryMovement object + timestamp

### Implementation

#### 1. Add import at top of alertAttacks.py

```python
import json
import os
from pathlib import Path
```

#### 2. Add debug logging function

```python
def log_movement_debug(militaryMovement, session):
    """
    Log full military movement data for debugging attack classification

    Creates/appends to ~/.ikabot_alert_debug.log with JSON data
    """
    try:
        log_file = Path.home() / ".ikabot_alert_debug.log"

        # Prepare log entry
        log_entry = {
            "timestamp": time.time(),
            "timestamp_readable": time.strftime("%Y-%m-%d %H:%M:%S"),
            "server": session.servidor,
            "world": session.mundo,
            "player": session.username,
            "movement": militaryMovement  # Full object
        }

        # Append to log file (JSON lines format)
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception as e:
        # Don't crash alertAttacks if logging fails
        print(f"Debug logging failed: {e}")
```

#### 3. Call it when alert triggers

**Location**: Line 131, right after detecting new attack

```python
if event_id not in knownAttacks:
    knownAttacks.append(event_id)

    # DEBUG: Log full movement data
    log_movement_debug(militaryMovement, session)

    # get information about the attack
    missionText = militaryMovement["event"]["missionText"]
    # ... rest of existing code
```

### Benefits

1. ✅ **Non-intrusive**: Doesn't change alert behavior
2. ✅ **Persistent**: Data saved to file for analysis
3. ✅ **Safe**: Wrapped in try-catch, won't crash bot
4. ✅ **Complete**: Captures entire data structure
5. ✅ **Timestamped**: Can correlate with alerts
6. ✅ **Multi-instance**: Each alert session appends

---

## Usage

### Step 1: Enable Debug Logging

Implement the feature (add ~30 lines to alertAttacks.py)

### Step 2: Trigger Alerts

Wait for attacks to occur (pirate or player)

### Step 3: Analyze Log File

```bash
# View log
cat ~/.ikabot_alert_debug.log

# Pretty print last entry
tail -1 ~/.ikabot_alert_debug.log | python -m json.tool

# Count entries
wc -l ~/.ikabot_alert_debug.log
```

### Step 4: Extract Detection Logic

From log data, identify:
- Fields that distinguish pirates from players
- Fields that indicate attack types
- Reliable detection patterns

### Step 5: Implement Classification

Update alertAttacks.py with discovered detection logic.

---

## Example Log Entry

```json
{
  "timestamp": 1699876543.123,
  "timestamp_readable": "2024-11-12 14:35:43",
  "server": "cz",
  "world": "Aeneas",
  "player": "pooky756",
  "movement": {
    "isHostile": true,
    "isOwnArmyOrFleet": false,
    "event": {
      "id": 12345,
      "missionText": "Přepadení (probíhá)",
      "missionType": "piracyRaid",  // <-- EXAMPLE: might exist
      "icon": "..."
    },
    "origin": {
      "id": 67890,
      "name": "Hr4fnsfj0rdur",
      "avatarName": "_K4_",
      "avatarId": 0,  // <-- EXAMPLE: might exist
      "type": "pirateFortress",  // <-- EXAMPLE: might exist
      "x": 50,
      "y": 50
    },
    "target": {
      "id": 11111,
      "name": "Řím",
      "x": 51,
      "y": 51
    },
    "army": {
      "amount": 0
    },
    "fleet": {
      "amount": 0,
      "ships": []
    },
    "eventTime": 1699880143,
    "remainingTime": 3600
  }
}
```

**From this we'd learn:**
- `origin["avatarId"] == 0` → pirate
- `origin["type"] == "pirateFortress"` → pirate
- `event["missionType"] == "piracyRaid"` → pirate
- `army["amount"] == 0 && fleet["amount"] == 0` → pirate

(These are hypothetical - actual structure TBD)

---

## Alternative: Telegram Debug Mode

Instead of file logging, send full data to Telegram:

```python
def log_movement_debug(militaryMovement, session):
    """Send full movement data to Telegram for debugging"""
    try:
        debug_msg = "=== DEBUG: ATTACK DETECTED ===\n"
        debug_msg += json.dumps(militaryMovement, indent=2)
        sendToBot(session, debug_msg)
    except Exception as e:
        print(f"Debug logging failed: {e}")
```

**Pros:**
- ✅ Immediate visibility
- ✅ No file management

**Cons:**
- ❌ Telegram message size limits
- ❌ Spam if many attacks
- ❌ Hard to search/analyze

**Recommendation**: Use file logging (more reliable).

---

## Configuration Option (Optional)

Add config flag to enable/disable debug logging:

```python
# ikabot/config.py
ALERT_DEBUG_LOGGING = True  # Set to False to disable

# In alertAttacks.py
from ikabot.config import ALERT_DEBUG_LOGGING

if ALERT_DEBUG_LOGGING:
    log_movement_debug(militaryMovement, session)
```

---

## Implementation Plan

### Phase 1: Basic Logging (15 min)
1. Add `log_movement_debug()` function
2. Call it when alert triggers
3. Test with one attack

### Phase 2: Data Collection (wait for attacks)
1. Let bot run with logging enabled
2. Collect 5-10 attack samples (mix of pirates/players)
3. Review log file

### Phase 3: Analysis (30 min)
1. Pretty-print log entries
2. Identify distinguishing fields
3. Document detection patterns

### Phase 4: Implementation (30 min)
1. Update alertAttacks.py with detection logic
2. Test with new attacks
3. Verify correct classification

**Total effort**: 1-2 hours + waiting time

---

## Success Criteria

- [ ] Debug logging implemented
- [ ] Log file created at `~/.ikabot_alert_debug.log`
- [ ] Captured at least 3 pirate attacks
- [ ] Captured at least 1 player attack (if possible)
- [ ] Identified reliable detection fields
- [ ] Documented detection patterns
- [ ] (Optional) Implemented classification in alertAttacks.py

---

## Security Considerations

### Data Sensitivity

Log file contains:
- ✅ Player usernames (yours and attackers)
- ✅ City names
- ✅ Coordinates
- ❌ No passwords or tokens

**Risk**: LOW (same data shown in game)

### Log File Location

**Current**: `~/.ikabot_alert_debug.log`

**Alternatives:**
- `~/.ikabot/` directory (keep with session data)
- `/tmp/ikabot_debug.log` (temporary)
- Custom path via config

**Recommendation**: Use `~/.ikabot/alert_debug.log` (alongside session file)

### Log Rotation

**Simple approach**: No rotation (manual cleanup)

**Enhanced approach** (optional):
```python
# Keep last 100 entries
def rotate_log(log_file, max_lines=100):
    if log_file.exists():
        lines = log_file.read_text().splitlines()
        if len(lines) > max_lines:
            log_file.write_text("\n".join(lines[-max_lines:]) + "\n")
```

---

## Code Diff Preview

```diff
# ikabot/function/alertAttacks.py

+import json
+from pathlib import Path
+
+def log_movement_debug(militaryMovement, session):
+    """Log full military movement data for debugging"""
+    try:
+        log_file = Path.home() / ".ikabot" / "alert_debug.log"
+        log_file.parent.mkdir(exist_ok=True)
+
+        log_entry = {
+            "timestamp": time.time(),
+            "timestamp_readable": time.strftime("%Y-%m-%d %H:%M:%S"),
+            "server": session.servidor,
+            "world": session.mundo,
+            "player": session.username,
+            "movement": militaryMovement
+        }
+
+        with open(log_file, "a") as f:
+            f.write(json.dumps(log_entry) + "\n")
+    except Exception as e:
+        pass  # Silent fail
+
 def do_it(session, minutes):
     thread = threading.Thread(target=respondToAttack, args=(session,))
     thread.start()

     knownAttacks = []
     while True:
         currentAttacks = []
         try:
             # ... existing code to get militaryMovements ...

             for militaryMovement in [
                 mov for mov in militaryMovements if mov["isHostile"]
             ]:
                 event_id = militaryMovement["event"]["id"]
                 currentAttacks.append(event_id)

                 if event_id not in knownAttacks:
                     knownAttacks.append(event_id)

+                    # DEBUG: Log full movement data
+                    log_movement_debug(militaryMovement, session)

                     # get information about the attack
                     missionText = militaryMovement["event"]["missionText"]
                     # ... rest unchanged ...
```

**Changes**: +28 lines, 0 lines removed, 0 lines modified

---

## Next Steps After Data Collection

Once log data reveals detection patterns:

1. **Update issue-04** with actual field names
2. **Implement classification** in alertAttacks.py
3. **Add tests** for different attack types
4. **Document** attack type detection for future devs
5. **Consider** keeping debug logging as permanent feature (configurable)

---

## Related Files

- **Primary**: `ikabot/function/alertAttacks.py`
- **Config**: `ikabot/config.py` (optional flag)
- **Log location**: `~/.ikabot/alert_debug.log`

---

**Created**: 2025-11-12
**Status**: Ready for Implementation
**Estimated Effort**: 15 minutes coding + waiting for attacks
**Risk**: NONE (logging only, no logic changes)
**Benefit**: HIGH (reveals actual API structure for proper fix)
