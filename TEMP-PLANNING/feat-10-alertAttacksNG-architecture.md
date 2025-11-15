# Feature #10: alertAttacksNG - Next Generation Attack Monitoring

**Status**: Planning - Architecture Complete
**Priority**: HIGH (implements before Feature #11)
**Difficulty**: 4/10
**Type**: Standalone Replacement Process
**Branch**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7` (pirate detection already implemented here)

---

## Problem Statement

**Current situation:**
- `alertAttacks.py` polls `militaryAdvisor` API every N minutes (default: 20 min)
- **5 other modules** also fetch the same data independently:
  1. `shipMovements.py` - fetches on user request
  2. `planRoutes.py` - fetches when planning routes
  3. `alertLowWine.py` - checks wine transports
  4. `attackBarbarians.py` - checks army movements
  5. `autoBarbarians.py` - checks barbarian missions

**The problem:**
- Data is fetched, used, then **discarded**
- Missed detection opportunity: If `shipMovements.py` fetches data showing an incoming attack, we don't detect it until the next `alertAttacks` poll (up to 20 min later!)
- Wasted opportunity: Multiple modules get the **exact same data** we need for attack detection
- alertAttacks cannot be easily enhanced (fork maintenance - upstream changes conflict)

**Example missed detection:**
```
14:00 - alertAttacks polls → no attack
14:05 - User calls shipMovements → data shows attack incoming! (but discarded)
14:10 - Attack could be detected here (5 min earlier)
14:20 - alertAttacks polls → detects attack (15 min late!)
```

---

## Solution Overview

**Create alertAttacksNG.py: Complete standalone replacement with dual-mode detection**

```
┌────────────────────────────────────────────────────────────────┐
│  alertAttacksNG.py (NEW STANDALONE PROCESS)                    │
│                                                                 │
│  Mode 1: Timer-Based Polling (like alertAttacks)              │
│    - User configures interval (default: 5 min)                │
│    - Fetches militaryAdvisor on schedule                      │
│    - Checks for attacks                                       │
│                                                                 │
│  Mode 2: Opportunistic Detection (NEW!)                       │
│    - Intercepts session.post() calls                          │
│    - Detects militaryAdvisor fetches from ANY module          │
│    - Checks immediately (with 10 sec cooldown)                │
│    - ZERO modifications to existing modules                   │
│                                                                 │
│  Implementation: Monkey-patch session.post()                  │
│    ↓                                                           │
│  When ANY module calls session.post("militaryAdvisor..."):    │
│    1. Original post executes normally                         │
│    2. NG intercepts response                                  │
│    3. Checks for attacks (if cooldown elapsed)                │
│    4. Returns response to caller                              │
│    5. Caller module unaware (zero changes needed)             │
└────────────────────────────────────────────────────────────────┘

                     Intercepted calls from:
        ┌────────────────┬────────────────┬────────────────┐
        │                │                │                │
   ┌────┴────┐     ┌────┴────┐     ┌────┴────┐     ┌────┴────┐
   │ ship    │     │ plan    │     │ alert   │     │ attack  │
   │ Movements│    │ Routes  │     │ LowWine │     │ Barbarians│
   └─────────┘     └─────────┘     └─────────┘     └─────────┘
   (on demand)     (planning)      (wine check)    (movements)

All modules work unchanged! Interceptor is transparent.
```

**Result:**
- Attack detected the moment **ANY** module fetches military data
- PLUS regular timer-based checking
- ZERO modifications to existing modules (perfect for fork!)

---

## Architecture: Dual-Mode Detection

### Mode 1: Timer-Based Polling (Preserve Existing Behavior)

**Just like alertAttacks:**
```python
while True:
    try:
        # Fetch militaryAdvisor on timer
        html = session.get()
        city_id = extract_city_id(html)
        url = "view=militaryAdvisor&currentCityId={}&actionRequest={}&ajax=1"
        response = session.post(url.format(city_id, actionRequest))
        movements = parse_response(response)

        # Check for attacks
        check_for_attacks(movements, source="timer")

    except Exception as e:
        # Log error, continue
        pass

    time.sleep(polling_interval)
```

**User configures:**
- Polling interval (default: 5 minutes, was 20 in alertAttacks)
- All existing alertAttacks options (vacation mode response, etc.)

---

### Mode 2: Opportunistic Detection (NEW!)

**Interceptor implementation:**
```python
class OpportunisticMonitor:
    def __init__(self, cooldown_seconds=10):
        self.last_check = 0
        self.cooldown = cooldown_seconds
        self.enabled = True

    def install_interceptor(self, session):
        """
        Monkey-patch session.post() to detect militaryAdvisor calls.
        This runs ONCE when alertAttacksNG starts.
        ZERO modifications to session.py or any other module!
        """
        # Save original method
        original_post = session.post
        monitor = self  # Capture for closure

        def intercepted_post(url='', payloadPost={}, params={}, **kwargs):
            # Always call original first (normal behavior)
            response = original_post(url, payloadPost, params, **kwargs)

            # Check if this is militaryAdvisor call
            if monitor.enabled and 'militaryAdvisor' in url:
                current_time = time.time()

                # Apply cooldown (prevent spam, user requirement: 10 sec)
                if current_time - monitor.last_check >= monitor.cooldown:
                    monitor.last_check = current_time

                    try:
                        # Parse response (same structure all modules use)
                        resp = json.loads(response, strict=False)
                        movements = resp[1][1][2]["viewScriptParams"]["militaryAndFleetMovements"]

                        # Check for attacks opportunistically
                        check_for_attacks(movements, source="opportunistic")
                    except Exception as e:
                        # CRITICAL: Don't break original functionality
                        # Just skip this opportunistic check
                        pass

            # Return response to caller (caller sees no difference)
            return response

        # Replace session method with interceptor
        session.post = intercepted_post
```

**Why this works:**
- `shipMovements.py` calls `session.post("militaryAdvisor...")` → interceptor triggers
- `planRoutes.py` calls `session.post("militaryAdvisor...")` → interceptor triggers
- ALL modules call same method → all automatically intercepted
- ZERO code changes to any existing module
- Perfect for fork (upstream changes don't conflict)

**Cooldown logic:**
- User requirement: Max once per 10 seconds (configurable)
- Prevents spam if multiple modules call simultaneously
- Timer-based checks don't count against cooldown (different mode)

---

## Migration Strategy: Parallel Testing

**alertAttacks vs alertAttacksNG - Side by Side Testing:**

### Phase 1: Initial Testing (Week 1)
```
Main Menu:
[1] Alert if attacked (STABLE - current alertAttacks)
[2] Alert Attacks NG (BETA - new dual-mode system)
[3] Ship movements
...

User starts BOTH processes:
- alertAttacks: polling every 20 min (old default)
- alertAttacksNG: polling every 5 min + opportunistic

Both send alerts independently:
✅ If attack detected, user gets TWO alerts (verification!)
✅ User notices NG is faster (5 min vs 20 min)
✅ User notices NG catches attacks when using other modules
```

**Observation checklist:**
- [ ] Both processes detect same attacks?
- [ ] No false positives from NG?
- [ ] Opportunistic detection working (alerts when using shipMovements)?
- [ ] No duplicate alerts from NG itself (cooldown working)?
- [ ] Process stable (no crashes)?

---

### Phase 2: Confidence Building (Week 2-3)
```
User stops alertAttacks, runs ONLY alertAttacksNG:
- Faster detection (5 min + opportunistic)
- Lower API load (opportunistic reuses existing calls)
- Same reliability as alertAttacks
```

**Test scenarios:**
1. Attack arrives, user AFK → Timer detects (within 5 min)
2. Attack arrives, user checking ships → Opportunistic detects (instant!)
3. Multiple attacks → All detected, classified correctly
4. Pirate + player simultaneously → Both alerted with correct messages
5. Own pirate missions → NOT alerted (correct behavior)

---

### Phase 3: Deprecation (Month 2+)
```
Main Menu:
[1] Alert if attacked (DEPRECATED - use NG)
[2] Alert Attacks NG (STABLE - recommended)
...

If user selects [1]:
"⚠️  alertAttacks is deprecated. alertAttacksNG offers:
  - Faster detection (5 min vs 20 min default)
  - Opportunistic detection (instant when using other modules)
  - Better pirate classification

Switch to alertAttacksNG? (Y/n)"
```

---

### Phase 4: Eventual Removal
**Options:**
1. Keep alertAttacks forever (low cost, user choice)
2. Remove when upstream removes it
3. Remove after 6 months of NG stability

**Recommendation:** Keep until upstream removes (minimal maintenance cost)

---

## File Structure

### New Files Created:

**`ikabot/function/alertAttacksNG.py`** (~400-500 lines)
```python
# Main process file, similar structure to alertAttacks.py

# Imports
from ikabot.helpers.attackMonitorState import StateManager
from ikabot.helpers.varios import *
from ikabot.helpers.botComm import *
import time, json, re

# Configuration function (like alertAttacks setup)
def alertAttacksNG(session, event, stdin_fd, predetermined_input):
    """User configuration and process launch"""
    # Prompt for timer interval
    # Prompt for opportunistic enable/disable
    # Prompt for opportunistic cooldown
    # Prompt for vacation mode option (existing)
    # Launch background process
    pass

# Background process loop
def run_monitor(session, config):
    """
    Dual-mode monitoring:
    - Timer-based polling
    - Opportunistic interception
    """
    # Install interceptor
    monitor = OpportunisticMonitor(cooldown_seconds=config['opportunistic_cooldown'])
    monitor.install_interceptor(session)

    # Load state
    state = StateManager()

    # Polling loop
    while True:
        # Timer-based check
        movements = fetch_military_advisor(session)
        check_for_attacks(session, movements, state, source="timer")

        time.sleep(config['polling_interval'])

# Opportunistic monitor class
class OpportunisticMonitor:
    """Intercepts session.post() calls"""
    # (as shown above)

# Attack detection logic
def check_for_attacks(session, movements, state, source="unknown"):
    """
    Unified attack detection for both modes.

    REUSE from current branch (alertAttacks.py):
    - Pirate vs player classification
    - Message formatting
    - knownAttacks tracking
    """
    new_attacks = []

    for movement in movements:
        # Filter hostile incoming
        if movement.get("isHostile") and not movement.get("isReturning"):
            event_id = movement["event"]["id"]

            # Check if already known
            if event_id not in state.known_attacks:
                # Classify pirate vs player (REUSE from current branch)
                is_pirate = classify_as_pirate(movement)

                # Build alert message (REUSE from current branch)
                message = build_alert_message(movement, is_pirate)

                # Send alert
                sendToBot(session, message)

                # Debug logging (optional)
                if config.get('debug_logging'):
                    log_attack_debug(movement, ...)

                # Mark as known
                state.add_known_attack(event_id, {
                    'detected_at': time.time(),
                    'source': source,
                    'is_pirate': is_pirate
                })

                new_attacks.append(event_id)

    # Cleanup old attacks (>24 hours)
    state.cleanup_old_attacks(max_age_hours=24)

    return new_attacks

# Helper functions
def classify_as_pirate(movement):
    """EXACT copy from current branch (alertAttacks.py line ~156)"""
    return (
        movement["event"].get("type") == "piracy" and
        movement["event"].get("missionIconClass") == "piracyRaid"
    )

def build_alert_message(movement, is_pirate):
    """EXACT copy from current branch (alertAttacks.py lines ~158-185)"""
    # Pirate message vs player message
    # (copy existing logic)
    pass

def log_attack_debug(movement, ...):
    """OPTIONAL: Copy from current branch if user wants debug logging"""
    # (copy existing logic from alertAttacks.py)
    pass
```

---

**`ikabot/helpers/attackMonitorState.py`** (~150 lines)
```python
# State management (file-based, survives restarts)

from pathlib import Path
import json
import time
import fcntl  # File locking for safety

STATE_FILE = Path.home() / ".ikabot_attack_monitor_state.json"

class StateManager:
    """Manages knownAttacks state across process restarts"""

    def __init__(self):
        self.state_file = STATE_FILE
        self.known_attacks = {}
        self.load()

    def load(self):
        """Load state from file with locking"""
        if not self.state_file.exists():
            self.known_attacks = {}
            return

        try:
            with open(self.state_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                data = json.load(f)
                self.known_attacks = data.get('known_attacks', {})
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            # Corrupted file, start fresh
            self.known_attacks = {}

    def save(self):
        """Save state to file with locking"""
        try:
            with open(self.state_file, 'w') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
                json.dump({
                    'known_attacks': self.known_attacks,
                    'last_updated': time.time()
                }, f, indent=2)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            # Log error but don't crash
            pass

    def add_known_attack(self, event_id, metadata):
        """Add attack to known list"""
        self.known_attacks[str(event_id)] = metadata
        self.save()

    def cleanup_old_attacks(self, max_age_hours=24):
        """Remove attacks older than max_age_hours"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        to_remove = []
        for event_id, metadata in self.known_attacks.items():
            detected_at = metadata.get('detected_at', 0)
            if current_time - detected_at > max_age_seconds:
                to_remove.append(event_id)

        if to_remove:
            for event_id in to_remove:
                del self.known_attacks[event_id]
            self.save()
```

---

### Modified Files:

**`ikabot/function/__init__.py`** (or menu file) - ADD to menu options:
```python
# Add to menu list (+2 lines):
[...existing menu items...]
{"name": "Alert Attacks NG (BETA)", "function": alertAttacksNG},
```

**Total modifications:** 2 lines in 1 file (menu registration)

---

## Configuration Options

**User prompts when starting alertAttacksNG:**

```
=== Alert Attacks NG (Next Generation) ===

This process monitors for incoming attacks with dual-mode detection:
- Timer: Regular polling (like classic alertAttacks)
- Opportunistic: Instant detection when other modules fetch data

[Timer Configuration]
How often should I poll militaryAdvisor? (minutes)
  Default: 5 (faster than classic 20)
  Minimum: 1
  > _

[Opportunistic Configuration]
Enable opportunistic detection? (Y/n)
  Detects attacks instantly when you use other modules
  (shipMovements, planRoutes, etc.)
  > _

[If enabled]
Opportunistic check cooldown? (seconds)
  Prevents spam if multiple modules run simultaneously
  Default: 10
  Minimum: 5
  > _

[Existing alertAttacks Options]
If attacked, send vacation mode activation code? (y/N)
  > _

[Debug Options]
Enable debug logging to file? (y/N)
  Logs all attack data to ~/ikalog/alert_debug.log
  > _

Starting Alert Attacks NG with:
- Timer: every 5 minutes
- Opportunistic: enabled (10 sec cooldown)
- Vacation mode: disabled
- Debug logging: disabled

Process running in background...
```

---

## State File Format

**`~/.ikabot_attack_monitor_state.json`:**
```json
{
  "known_attacks": {
    "123456": {
      "detected_at": 1699999999.123,
      "source": "opportunistic:shipMovements",
      "is_pirate": true,
      "event_type": "piracy",
      "mission_icon": "piracyRaid"
    },
    "123457": {
      "detected_at": 1699999888.456,
      "source": "timer",
      "is_pirate": false,
      "event_type": "attack",
      "mission_icon": "attack"
    }
  },
  "last_updated": 1699999999.789
}
```

**Cleanup strategy:**
- Remove attacks older than 24 hours (safe - attacks complete by then)
- Cleanup runs every check (minimal overhead)
- Prevents file growing forever

---

## Code Reuse from Current Branch

**From `alertAttacks.py` on `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`:**

✅ **Pirate classification** (lines ~156-160):
```python
isPirate = (
    militaryMovement["event"].get("type") == "piracy" and
    militaryMovement["event"].get("missionIconClass") == "piracyRaid"
)
```

✅ **Alert messages** (lines ~162-185):
```python
if isPirate:
    msg = "-- PIRATE ATTACK --\n"
    msg += "from the pirate fortress {} of {}\n".format(origin["name"], origin["avatarName"])
    msg += "(Pirate attacks cannot show unit/fleet numbers)\n"
else:
    msg = "-- ALERT --\n"
    msg += "from the city {} of {}\n".format(origin["name"], origin["avatarName"])
    msg += "{} units\n{} fleet\n".format(amountTroops, amountFleets)
    msg += "If you want to put the account in vacation mode send:\n{:d}:1".format(os.getpid())
```

✅ **Debug logging** (lines ~21-178 - OPTIONAL):
```python
def log_attack_debug(militaryMovement, all_movements, postdata, session, current_city_id, time_now, time_left):
    # Complete implementation already exists
    # Copy if user wants debug logging
```

✅ **KnownAttacks pattern** (alertAttacks.py existing logic):
```python
# Check if already alerted
if event_id in knownAttacks:
    continue

# Add to known after alerting
knownAttacks.append(event_id)
```

**All logic PROVEN working on current branch → just copy to alertAttacksNG.py**

---

## Benefits of alertAttacksNG

### vs alertAttacks (Classic):

| Feature | alertAttacks | alertAttacksNG |
|---------|-------------|----------------|
| Background process | ✅ Yes | ✅ Yes |
| Timer-based polling | ✅ Yes (20 min default) | ✅ Yes (5 min default) |
| Opportunistic checks | ❌ No | ✅ Yes (instant!) |
| Pirate detection | ❌ No (0 units/fleet) | ✅ Yes (classified) |
| Vacation mode option | ✅ Yes | ✅ Yes |
| Telegram alerts | ✅ Yes | ✅ Yes |
| State persistence | ⚠️ In-memory only | ✅ File-based |
| Debug logging | ❌ No | ✅ Yes (optional) |
| Modifications to other files | N/A | ✅ 0 lines! |
| Fork-friendly | ⚠️ Medium (old code) | ✅ Perfect (separate file) |
| Auto crew conversion defense | ❌ No | ✅ Ready (Feature 11) |

### Speed Improvements:

**Scenario 1: Timer only (user doesn't use other modules)**
- Classic: 20 min average detection delay
- NG: 5 min average detection delay (default)
- **Improvement: 4x faster**

**Scenario 2: Opportunistic (user checks ships during attack window)**
- Classic: Up to 20 min delay
- NG: Instant detection (0 delay)
- **Improvement: Infinite (instant vs delayed)**

**Scenario 3: Mixed usage**
- Attack appears at 14:00
- User checks shipMovements at 14:03
- Classic: Detected at 14:20 (20 min delay)
- NG: Detected at 14:03 (3 min delay, opportunistic)
- **Improvement: 17 minutes gained**

---

## Fork Maintenance Benefits

**Why this architecture is PERFECT for a fork:**

### Zero Modifications to Upstream Files:
```
Files from upstream (unchanged):
✅ ikabot/function/shipMovements.py (0 changes)
✅ ikabot/function/planRoutes.py (0 changes)
✅ ikabot/function/alertLowWine.py (0 changes)
✅ ikabot/function/attackBarbarians.py (0 changes)
✅ ikabot/function/autoBarbarians.py (0 changes)
✅ ikabot/web/session.py (0 changes)
✅ ikabot/function/alertAttacks.py (0 changes - kept for compatibility)

Files fork-specific:
📁 ikabot/function/alertAttacksNG.py (NEW - all our code)
📁 ikabot/helpers/attackMonitorState.py (NEW - all our code)
📝 ikabot/function/__init__.py (2 lines - menu entry)
```

### Merge Strategy:
1. **Upstream updates any module** → Pull changes → No conflicts! (we didn't modify)
2. **Upstream updates menu** → Minimal conflict (just menu entry)
3. **Upstream removes alertAttacks** → No problem! (we have NG)
4. **Upstream adds new feature** → Pull changes → Works with NG automatically (interceptor catches new modules too!)

### Example: Upstream adds new module `attackPlayers.py`:
```python
# New upstream module fetches militaryAdvisor
def attackPlayers(session):
    response = session.post("view=militaryAdvisor...")
    movements = parse(response)
    # ... logic ...
```

**Without any changes:**
- alertAttacksNG interceptor catches this call automatically!
- New module opportunistically feeds attack detection
- Zero code changes needed in fork

**This is the key advantage!** Interceptor approach is future-proof.

---

## Testing Plan

### Test Cases:

**1. Timer-based detection (classic behavior)**
- Start alertAttacksNG (5 min interval)
- Wait for attack to appear
- Verify detected within 5 minutes
- Verify correct classification (pirate/player)
- Verify correct message format
- Verify no duplicate alerts

**2. Opportunistic detection (new feature)**
- Start alertAttacksNG (20 min interval to avoid timer)
- Attack appears
- Within 1 minute, run shipMovements
- Verify attack detected instantly (opportunistic)
- Wait for timer (20 min)
- Verify NO duplicate alert (knownAttacks working)

**3. Cooldown enforcement**
- Start alertAttacksNG (10 sec cooldown)
- Run shipMovements (triggers opportunistic check)
- Immediately run planRoutes (within 10 sec)
- Verify only ONE check performed (cooldown working)
- Wait 11 seconds
- Run alertLowWine
- Verify check performed (cooldown elapsed)

**4. Parallel testing with classic**
- Start alertAttacks (20 min interval)
- Start alertAttacksNG (5 min interval + opportunistic)
- Attack appears
- Verify BOTH processes alert
- Verify NG alerts first (faster)
- Verify classic alerts eventually (slower)

**5. State persistence**
- Start alertAttacksNG
- Attack detected, alerted
- Kill alertAttacksNG process
- Restart alertAttacksNG
- Verify state file loaded
- Verify attack NOT re-alerted (state persisted)

**6. Multiple simultaneous attacks**
- Pirate attack on city A
- Player attack on city B
- Verify both detected
- Verify correct classification for each
- Verify distinct messages
- Verify both in state file

**7. Own pirate missions (false positive check)**
- Start alertAttacksNG
- User sends pirate mission from own fortress
- Verify NO alert (isOwnArmyOrFleet filter working)

**8. Debug logging (optional feature)**
- Enable debug logging in config
- Attack appears
- Verify ~/ikalog/alert_debug.log created
- Verify comprehensive data logged (same as current branch)
- Disable debug logging
- Attack appears
- Verify no log file created/updated

**9. Interceptor stability**
- Start alertAttacksNG (installs interceptor)
- Run shipMovements 100 times
- Verify no crashes
- Verify all calls succeed
- Verify shipMovements functions normally (unaware of interception)

**10. Cleanup old attacks**
- Manually create state file with attack from 25 hours ago
- Start alertAttacksNG
- Check state file after first cycle
- Verify old attack removed (>24 hour cleanup)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Monkey-patch breaks session | Low | High | Extensive testing, try-except in interceptor |
| Interceptor affects performance | Low | Low | Minimal overhead (cooldown, simple JSON parse) |
| State file corruption | Low | Medium | File locking, try-except, recover gracefully |
| Duplicate alerts | Low | Medium | Robust knownAttacks + cooldown |
| Process crashes | Low | High | Error handling, don't break on intercept failure |
| Upstream conflicts (fork) | Very Low | Low | ZERO modifications to upstream files |
| User confusion (two processes) | Medium | Low | Clear messaging, deprecation warnings |

**Overall Risk:** LOW

**Critical safeguards:**
1. Interceptor wrapped in try-except (never break caller)
2. File locking on state (prevent corruption)
3. Cooldown prevents spam
4. Parallel testing phase (build confidence)
5. Keep alertAttacks available (fallback)

---

## Implementation Phases

### Phase 1: Core Implementation (Week 1)
- [ ] Create `alertAttacksNG.py` structure
- [ ] Create `attackMonitorState.py` (state management)
- [ ] Copy detection logic from alertAttacks.py (current branch)
- [ ] Implement timer-based polling (Mode 1)
- [ ] Test basic detection (timer only)

### Phase 2: Opportunistic Mode (Week 1-2)
- [ ] Implement OpportunisticMonitor class
- [ ] Implement session.post() interceptor
- [ ] Implement cooldown logic
- [ ] Test opportunistic detection
- [ ] Test cooldown enforcement

### Phase 3: Integration (Week 2)
- [ ] Add to menu system
- [ ] User configuration prompts
- [ ] State file persistence
- [ ] Cleanup old attacks logic
- [ ] Test state persistence across restarts

### Phase 4: Testing (Week 2-3)
- [ ] Run all test cases
- [ ] Parallel testing with alertAttacks
- [ ] Real-world testing (detect actual attacks)
- [ ] Performance testing (100+ intercepts)
- [ ] Edge case testing

### Phase 5: Documentation (Week 3)
- [ ] Code comments
- [ ] User documentation (if needed)
- [ ] Update planning docs with results
- [ ] Prepare for Feature 11 (crew conversion defense integration)

---

## Dependencies

**Required before starting:**
- ✅ Pirate detection working (current branch)
- ✅ Alert message formatting (current branch)
- ✅ Debug logging (current branch - optional copy)
- ✅ Understanding of session.post() flow

**Blocks:**
- Feature #11 (crew conversion defense) - integrates with alertAttacksNG (already working in alertAttacks)

---

## Technical Questions (Resolved in Discussion)

### Q1: Should we modify existing modules to feed data?
**A:** NO - Use interceptor approach (monkey-patch session.post)
- Zero modifications to existing modules
- Future-proof (catches new modules automatically)
- Perfect for fork maintenance

### Q2: Helper module or standalone process?
**A:** Standalone process (complete replacement for alertAttacks)
- Easier testing (run both in parallel)
- Clearer migration path
- Independent lifecycle

### Q3: Default opportunistic ON or OFF?
**A:** ON by default
- Better user experience (faster detection)
- User can disable if desired
- Cooldown prevents spam

### Q4: Cooldown duration?
**A:** 10 seconds default (user configurable)
- User requirement from discussion
- Balances speed vs spam prevention
- Minimum: 5 seconds

### Q5: State management approach?
**A:** File-based (`~/.ikabot_attack_monitor_state.json`)
- Survives process restarts
- Simple JSON format
- File locking for safety
- Cleanup old attacks (>24 hours)

### Q6: Keep alertAttacks or remove?
**A:** Keep for parallel testing, deprecate later
- Phase 1-2: Both available
- Phase 3: NG recommended, classic deprecated
- Phase 4: Remove when upstream removes (or after 6 months)

---

## Success Criteria

**Phase 1 (Core) Success:**
- [ ] alertAttacksNG detects attacks via timer
- [ ] Correct pirate vs player classification
- [ ] Correct alert messages
- [ ] No crashes in 24 hour test
- [ ] State persists across restarts

**Phase 2 (Opportunistic) Success:**
- [ ] Interceptor catches militaryAdvisor calls
- [ ] Cooldown prevents spam
- [ ] No impact on intercepted modules (transparent)
- [ ] Opportunistic detection faster than timer

**Phase 3 (Integration) Success:**
- [ ] User can configure both modes
- [ ] Clean menu integration
- [ ] State file management working
- [ ] Old attacks cleaned up automatically

**Phase 4 (Production Ready) Success:**
- [ ] All test cases pass
- [ ] No duplicate alerts in 1 week parallel testing
- [ ] User reports faster detection
- [ ] No crashes or errors in logs
- [ ] Ready for Feature 11 integration (crew conversion defense)

---

## Future Enhancements (Out of Scope)

1. **Feature #11: Crew conversion defense integration** (next feature)
   - Integrates existing crew conversion with alertAttacksNG detection
   - Emergency crew conversion on attack detection (~20 lines to copy from alertAttacks)

2. **Multi-account support**
   - Separate state files per account
   - Separate interceptors per session

3. **Attack analytics**
   - Track detection source distribution (timer vs opportunistic)
   - Average detection delay
   - Attack frequency statistics

4. **Configurable cleanup**
   - User sets max age for knownAttacks
   - Manual cleanup command

5. **Web dashboard**
   - View current state (knownAttacks)
   - View detection statistics
   - View last opportunistic check time

---

**Created**: 2025-11-15
**Status**: Planning - Architecture Complete, Ready for Implementation
**Next**: Begin Phase 1 Implementation (Core)
**Branch**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7` (has working pirate detection to copy)

---

## Summary

**What:** alertAttacksNG - Complete replacement for alertAttacks with dual-mode detection

**Why:**
- Faster detection (5 min timer + instant opportunistic)
- Better pirate classification
- Fork-friendly (zero modifications to upstream files)
- Future-proof (interceptor catches new modules automatically)

**How:**
- Standalone background process
- Timer polling (like alertAttacks)
- Interceptor for opportunistic detection (monkey-patch session.post)
- File-based state management
- Parallel testing with classic alertAttacks

**Risk:** Low (interceptor safeguards, parallel testing, minimal upstream changes)

**Benefit:** 4x faster average detection (timer) + infinite faster (opportunistic) = best of both worlds!

This is the foundation for Feature #11 (crew conversion defense integration) and all future attack-related enhancements.

**Note**: Crew conversion defense is already implemented and working in alertAttacks.py. Feature #11 will simply copy the trigger code (~20 lines) to alertAttacksNG when it's ready.
