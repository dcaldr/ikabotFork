# Feature #10: Parallel Attack Monitoring (Faster Detection)

**Status**: Planning - Overview Complete
**Priority**: HIGH (implements before Feature #11)
**Difficulty**: 3/10
**Type**: Architecture Refactor + Feature Enhancement
**Branch**: TBD (will create when implementing)

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

**Example missed detection:**
```
14:00 - alertAttacks polls → no attack
14:05 - User calls shipMovements → data shows attack incoming! (but discarded)
14:10 - Attack could be detected here (5 min earlier)
14:20 - alertAttacks polls → detects attack (15 min late!)
```

---

## Solution Overview

**Create centralized attack detection that ALL modules can feed:**

```
┌─────────────────────────────────────────────────────────┐
│  ikabot/helpers/militaryMonitor.py (NEW FILE)           │
│                                                          │
│  def check_for_attacks(movements, time_now, ...):       │
│    - Classify pirate vs player (existing logic)         │
│    - Check knownAttacks (prevent duplicates)            │
│    - Send appropriate alert                             │
│    - Log to debug file (if enabled)                     │
│    - Return detection result                            │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ feed data
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────┴────┐      ┌────┴────┐      ┌────┴────┐
   │ alert   │      │ ship    │      │ plan    │
   │ Attacks │      │ Movements│     │ Routes  │
   └─────────┘      └─────────┘      └─────────┘
   (polls           (on demand)      (planning)
   every 20m)
```

**Result:** Attack detected the moment **ANY** module fetches military data, not just when alertAttacks polls.

---

## Implementation Order (Feature 2 → Feature 1)

### Why This Order?

1. **Lower merge conflict risk**
   - Refactor `alertAttacks.py` ONCE (Feature 2), then leave it alone
   - Feature 1 adds code to NEW file (`militaryMonitor.py`), not existing files

2. **Better architecture**
   - Feature 2 creates centralized detection
   - Feature 1 adds emergency response to that central location
   - Clean separation of concerns

3. **Immediate benefit**
   - Feature 2: Faster detection for ALL attacks (not just pirates)
   - Feature 1: Only helps when pirates detected

---

## Feature 2 Implementation Plan (HIGH LEVEL)

### Phase 1: Create Detection Module

**File:** `ikabot/helpers/militaryMonitor.py` (NEW)

**Functions needed:**
```python
def check_for_attacks(movements, time_now, postdata, session, city_id):
    """
    Centralized attack detection called by any module with military data.

    Parameters:
    - movements: militaryMovements array from API
    - time_now: server timestamp
    - postdata: full API response
    - session: session object
    - city_id: current city ID

    Returns:
    - dict with detection results (for caller to use if needed)
    """
    # 1. Filter hostile movements
    # 2. Check knownAttacks (prevent duplicate alerts)
    # 3. For each NEW attack:
    #    - Extract data
    #    - Classify pirate vs player
    #    - Build appropriate message
    #    - Send alert
    #    - Log if debug enabled
    # 4. Clean up old attacks
    # 5. Return results
```

**State management:**
- `knownAttacks` list needs to be **shared** across calls
- Options:
  - A) Global variable (simple but not ideal)
  - B) File-based state (`~/.ikabot/known_attacks.json`)
  - C) In-memory cache with process communication
- **Recommended:** Option B (file-based, survives restarts)

**Debug logging:**
- Move `log_attack_debug()` function FROM `alertAttacks.py` TO `militaryMonitor.py`
- Keep same functionality, centralize in one place

---

### Phase 2: Extract Detection Logic from alertAttacks.py

**Current code in alertAttacks.py (lines 107-185):**
- Fetches militaryAdvisor data
- Loops through hostile movements
- Checks knownAttacks
- Classifies pirate vs player
- Builds message
- Sends alert
- Logs debug data

**After refactor:**
```python
# alertAttacks.py do_it() function becomes simpler:

while True:
    try:
        # Fetch military data (existing code)
        html = session.get()
        city_id = re.search(r"currentCityId:\s(\d+),", html).group(1)
        url = "view=militaryAdvisor&..."
        movements_response = session.post(url)
        postdata = json.loads(movements_response, strict=False)
        militaryMovements = postdata[1][1][2]["viewScriptParams"]["militaryAndFleetMovements"]
        timeNow = int(postdata[0][1]["time"])

        # NEW: Call centralized detection (replaces 80+ lines)
        from ikabot.helpers import militaryMonitor
        militaryMonitor.check_for_attacks(militaryMovements, timeNow, postdata, session, city_id)

    except Exception as e:
        # error handling

    time.sleep(minutes * 60)
```

**Lines reduced:** ~80 lines → ~15 lines
**alertAttacks.py changes:** Minimal, focused on polling loop only

---

### Phase 3: Add Data Feeding from Other Modules

**Modules to modify (1 line each):**

1. **shipMovements.py** (line ~65)
```python
movements = resp[1][1][2]["viewScriptParams"]["militaryAndFleetMovements"]
time_now = int(resp[0][1]["time"])
# ADD:
from ikabot.helpers import militaryMonitor
militaryMonitor.check_for_attacks(movements, time_now, resp, session, cityId)
```

2. **planRoutes.py** (line ~208)
```python
militaryMovements = postdata[1][1][2]["viewScriptParams"]["militaryAndFleetMovements"]
current_time = int(postdata[0][1]["time"])
# ADD:
from ikabot.helpers import militaryMonitor
militaryMonitor.check_for_attacks(militaryMovements, current_time, postdata, session, idCiudad)
```

3. **alertLowWine.py** (line ~93)
```python
movements = resp[1][1][2]["viewScriptParams"]["militaryAndFleetMovements"]
# ADD:
time_now = int(resp[0][1]["time"])  # extract time
from ikabot.helpers import militaryMonitor
militaryMonitor.check_for_attacks(movements, time_now, resp, session, cityId)
```

4. **attackBarbarians.py** (line ~430)
```python
movements = resp[1][1][2]["viewScriptParams"]["militaryAndFleetMovements"]
# ADD:
time_now = int(resp[0][1]["time"])  # extract time
from ikabot.helpers import militaryMonitor
militaryMonitor.check_for_attacks(movements, time_now, resp, session, city_id)
```

5. **autoBarbarians.py** (similar pattern if applicable)

**Total new lines:** ~5-10 lines across 5 files
**Complexity:** Very low (simple function call)

---

## Files Modified Summary (Feature 2)

| File | Type | Changes | Risk |
|------|------|---------|------|
| `ikabot/helpers/militaryMonitor.py` | **NEW** | ~150 lines (detection logic) | None |
| `ikabot/function/alertAttacks.py` | MODIFY | Extract logic, add call (~20 net lines changed) | LOW |
| `ikabot/function/shipMovements.py` | MODIFY | +3 lines (call monitor) | VERY LOW |
| `ikabot/function/planRoutes.py` | MODIFY | +3 lines (call monitor) | VERY LOW |
| `ikabot/function/alertLowWine.py` | MODIFY | +4 lines (extract time, call monitor) | VERY LOW |
| `ikabot/function/attackBarbarians.py` | MODIFY | +4 lines (extract time, call monitor) | VERY LOW |

**Total:**
- 1 new file
- 6 modified files
- ~170 new lines total
- Merge conflict risk: **LOW** (mostly new code)

---

## Benefits of Feature 2

### Immediate Benefits:
1. **Faster attack detection** - detect the moment ANY module fetches data
2. **Reduced server load** - no new API calls, reuse existing fetches
3. **Cleaner architecture** - centralized detection logic
4. **Easier maintenance** - one place to update detection logic

### Example Speed Improvement:
**Before:**
- Attack appears at 14:00
- alertAttacks polls at 14:20 → detected after 20 minutes

**After:**
- Attack appears at 14:00
- User checks shipMovements at 14:05 → **detected after 5 minutes!**
- 15 minutes faster detection

### Foundation for Feature 1:
- Feature 1 (auto-buy pirates) needs fast detection
- Feature 2 provides that foundation
- Feature 1 then just adds emergency response logic to `militaryMonitor.py`

---

## Testing Plan

### Test Cases:

1. **Polling detection (alertAttacks)**
   - Start alertAttacks
   - Wait for pirate attack
   - Verify alert sent
   - Verify no duplicates

2. **Opportunistic detection (other modules)**
   - Start alertAttacks (20min interval)
   - Attack appears
   - User calls shipMovements before next poll
   - Verify attack detected immediately
   - Verify not detected again when alertAttacks polls

3. **Duplicate prevention**
   - Attack detected by shipMovements
   - 5 minutes later, alertAttacks polls
   - Verify NO duplicate alert

4. **State persistence**
   - Attack detected
   - Restart ikabot
   - Start alertAttacks again
   - Verify attack NOT re-alerted

5. **Multiple attacks**
   - Pirate attack + player attack simultaneously
   - Verify both detected with correct classification
   - Verify correct messages sent

---

## Technical Details to Investigate (Phase 2 Deep Dive)

### Questions to Answer:

1. **State management:**
   - How to share `knownAttacks` across modules?
   - File-based or in-memory?
   - Format: JSON, pickle, simple text?
   - Location: `~/.ikabot/known_attacks.json`?

2. **Process coordination:**
   - alertAttacks runs as background process
   - Other modules run in main process
   - How do they share state?
   - Need file locking?

3. **Cleanup strategy:**
   - When to remove old attacks from knownAttacks?
   - Time-based (attack older than 24h)?
   - Movement-based (not in current movements)?

4. **Error handling:**
   - What if monitor crashes?
   - Should it fail silently or alert?
   - How to prevent breaking calling modules?

5. **Configuration:**
   - Add to `config.py`?
   - Enable/disable parallel monitoring?
   - Debug logging on/off?

6. **Backwards compatibility:**
   - What if user updates but doesn't restart alertAttacks?
   - Graceful degradation?

---

## Next Steps

### Phase 1: Deep Investigation (NEXT TASK)
- Research state management options
- Test process communication
- Analyze exact data flow in each module
- Determine optimal architecture

### Phase 2: Implementation
- Create `militaryMonitor.py`
- Extract logic from `alertAttacks.py`
- Add calls from 5 data sources
- Test thoroughly

### Phase 3: Documentation & Cleanup
- Update README if needed
- Add code comments
- Remove debug logging code (or make optional)

---

## Dependencies

**Required before starting:**
- Current pirate detection working (✅ DONE)
- Debug logging analysis complete (✅ DONE)
- Understanding of all 5 data sources (⏳ NEEDS INVESTIGATION)

**Blocks:**
- Feature #11 (auto-buy pirates) - waits for this foundation

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| State sharing issues | Medium | High | Thorough testing, file locking |
| Duplicate alerts | Low | Medium | Robust knownAttacks check |
| Process coordination bugs | Medium | Medium | Simple file-based state |
| Breaking existing modules | Low | High | Minimal changes, error handling |
| Merge conflicts (fork) | Low | Low | New file + small changes |

**Overall Risk:** LOW-MEDIUM

---

**Created**: 2025-11-14
**Status**: Planning - Ready for Deep Investigation
**Next**: Investigate technical details, create detailed implementation plan
