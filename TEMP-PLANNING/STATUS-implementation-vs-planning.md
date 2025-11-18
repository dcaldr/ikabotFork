# Implementation Status: What's Done vs What's Planned

**Last Updated**: 2025-11-15
**Current Branch**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`

---

## TL;DR Summary

| Feature | Planning Status | Implementation Status | Location |
|---------|----------------|----------------------|----------|
| **Pirate Detection** | ✅ Documented | ✅ **DONE** | Current branch |
| **Debug Logging** | ✅ Documented | ✅ **DONE** | Current branch |
| **alertAttacksNG** (dual-mode) | ✅ **NEW** Architecture Complete | ❌ Not Started | Planning only |
| **Auto-Buy Pirates** (Feature 11) | ✅ Documented | ❌ Not Started | Planning only |
| **Crew Conversion Defense** | ⚠️ Different planning doc | ✅ **DONE** | Different branch! |

**KEY FINDING**: Another branch (`claude/auto-train-defense-01B2FzQ1cMSE1xLwvcXrRM1b`) has ALREADY implemented automatic pirate defense, but using a **different approach** than our current planning docs!

---

## What's Implemented on Current Branch

### ✅ DONE: Pirate Detection & Classification

**Branch**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`

**Implemented in**: `ikabot/function/alertAttacks.py`

**What works:**
```python
# Pirate classification (lines 321-324)
isPirate = (
    militaryMovement["event"].get("type") == "piracy" and
    militaryMovement["event"].get("missionIconClass") == "piracyRaid"
)

# Different alerts for pirates vs players (lines 327-350)
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

**Features:**
- ✅ Reliable pirate detection using `event.type` and `event.missionIconClass`
- ✅ Different alert messages for pirate vs player attacks
- ✅ Explains why pirate attacks show "0 units 0 fleet"
- ✅ Includes vacation mode option for player attacks (but not pirates)

**Commits:**
- `3d0295b` - Implement pirate attack classification in alerts
- `03f1ee8` - Add pirate detection fields and analysis based on captured data
- `dd1d75c` - Add precise timing data to debug log

---

### ✅ DONE: Debug Logging

**Branch**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`

**Implemented in**: `ikabot/function/alertAttacks.py` (lines 21-178)

**What works:**
```python
def log_attack_debug(militaryMovement, all_movements, postdata, session,
                     current_city_id, time_now, time_left):
    """Log EVERYTHING related to attack detection for debugging"""

    log_entry = {
        "timestamp": time.time(),
        "session": {...},
        "triggered_movement": militaryMovement,
        "all_movements": all_movements,
        "stats": {...},
        "raw_api_response": postdata,
        "quick_ref": {
            "event_type": militaryMovement.get("event", {}).get("type"),
            "event_mission_icon": militaryMovement.get("event", {}).get("missionIconClass"),
            "hide_units": militaryMovement.get("hideUnits"),
            # ... many more fields
        },
        "pirate_indicators": {
            "is_piracy_type": militaryMovement.get("event", {}).get("type") == "piracy",
            "is_piracy_icon": militaryMovement.get("event", {}).get("missionIconClass") == "piracyRaid",
            "likely_pirate": (both conditions)
        },
        "timing": {...},
        "available_keys": {...}
    }

    # Writes to ~/ikalog/alert_debug.log in JSON Lines format
```

**Features:**
- ✅ Comprehensive logging of all attack data
- ✅ JSON Lines format (one JSON object per line)
- ✅ Includes full API response for analysis
- ✅ Pre-computed pirate indicators for quick reference
- ✅ Precise timing data (seconds until arrival)
- ✅ Logs to `~/ikalog/alert_debug.log`

**Status**: Working, used for initial pirate detection research. Can be kept or made optional.

---

## What's Planned (This Branch)

### 📋 PLANNED: alertAttacksNG (Feature #10)

**Planning Doc**: `TEMP-PLANNING/feat-10-alertAttacksNG-architecture.md` (976 lines)

**Status**: ❌ Not started (planning complete, ready to implement)

**What it will be:**
- **Standalone replacement** for alertAttacks.py (not a helper module)
- **Dual-mode detection:**
  1. **Timer-based polling** (like alertAttacks, default 5 min)
  2. **Opportunistic detection** (intercepts `session.post()` calls to militaryAdvisor)
- **Zero modifications** to existing modules (perfect for fork!)
- **Monkey-patch approach**: Wraps `session.post()` when NG starts
- **10 second cooldown** on opportunistic checks (configurable)
- **File-based state**: `~/.ikabot_attack_monitor_state.json`
- **Parallel testing**: Can run alongside alertAttacks for verification

**Files to create:**
- `ikabot/function/alertAttacksNG.py` (~400-500 lines)
- `ikabot/helpers/attackMonitorState.py` (~150 lines)
- Menu modification: 2 lines

**Benefits:**
- 4x faster detection (5 min vs 20 min default timer)
- Instant detection when using other modules (shipMovements, planRoutes, etc.)
- Fork-friendly (no changes to upstream files)
- Future-proof (automatically catches new modules)

**Migration Plan:**
1. Run both alertAttacks + alertAttacksNG in parallel (testing)
2. Verify NG catches everything (build confidence)
3. Deprecate alertAttacks
4. Eventually remove (or keep for compatibility)

---

### 📋 PLANNED: Auto-Buy Pirates (Feature #11)

**Planning Doc**: `TEMP-PLANNING/feat-11-auto-buy-pirates-on-detection.md` (542 lines)

**Status**: ❌ Not started (planning complete, depends on Feature #10)

**What it will do:**
- Automatically **recruit pirates from pirate fortress** when attack detected
- **Send pirate mission** that completes before attack arrives
- **Spending limits**: Configurable max capture points per attack
- **Safety buffer**: Don't buy if attack too close (default 5 min)
- **Mission selection**: Pick fastest mission that completes in time

**Integration:**
- Adds to `alertAttacksNG.py` (builds on Feature #10)
- Reuses code from existing `autoPirate.py`
- 3-line addition to detection logic

**Files to modify:**
- `ikabot/function/alertAttacksNG.py` (+~100 lines)
- `ikabot/config.py` (+3 lines config options)

**Example workflow:**
```
14:00 - Pirate attack detected, arrives in 30 minutes
14:00:05 - Auto-buy triggers instantly
14:00:10 - Selects mission 1 (2m 30s duration)
14:02:40 - Pirates return from mission
14:30 - Attack arrives (27m 30s defense window!)
```

vs manual:
```
14:00 - Pirate attack detected
14:20 - User finally responds (20 min late)
14:22:30 - Pirates return
14:30 - Attack arrives (only 7m 30s defense window)
```

**Status**: Waiting for Feature #10 (alertAttacksNG) to be implemented first.

---

## What's Implemented (Different Branch!) 🔍

### ✅ DONE: Auto Crew Conversion Defense

**Branch**: `claude/auto-train-defense-01B2FzQ1cMSE1xLwvcXrRM1b` ⚠️ **DIFFERENT BRANCH!**

**Planning Doc**: `PLANNING-AUTO-TRAIN-DEFENSE.md` (on that branch)

**Implementation Status**: ✅ **FULLY IMPLEMENTED AND WORKING**

**What it does (DIFFERENT APPROACH!):**
- Automatically **converts capture points to crew strength** when pirate detected
- Does **NOT send pirate missions** (different from our Feature #11 plan!)
- Uses **crew conversion** feature of pirate fortress
- **Dual-mode operation:**
  1. **Automatic**: Called by alertAttacks when pirate detected
  2. **Manual**: Menu option 12.3 "Emergency Pirate Defense"

**Files created:**
```
ikabot/function/emergencyDefense.py (283 lines)
  - User-callable manual defense command
  - Configuration interface
  - Calls helper module for actual defense

ikabot/helpers/pirateDefense.py (~300 lines)
  - get_pirate_fortress_city() - finds fortress
  - get_conversion_data() - fetches conversion parameters from API
  - calculate_max_crew_conversion() - time-based calculation
  - convert_crew_for_defense() - executes conversion
  - auto_defend_pirate_attack() - main defense function
  - format_defense_result() - formats result for alerting
```

**Files modified:**
```
ikabot/function/alertAttacks.py
  - Imports: from ikabot.function.emergencyDefense import auto_defend_on_detection
  - Imports: from ikabot.helpers.pirateDefense import format_defense_result
  - When pirate detected, calls auto_defend_on_detection()
  - Appends defense result to alert message
```

**How it works:**
```python
# In alertAttacks.py when pirate detected:
if isPirate:
    try:
        pirate_attack_data = {
            "target_city_id": target["cityId"],
            "time_left": timeLeft,
            "origin_name": origin["name"],
            "target_name": target["name"]
        }
        defense_result = auto_defend_on_detection(session, pirate_attack_data)
        msg += format_defense_result(defense_result)
    except Exception as e:
        msg += f"\n--- AUTO-DEFENSE ERROR ---\n{str(e)}\n"
```

**Configuration (stored in session data):**
```python
session_data["auto_pirate_defense"] = {
    "enabled": True/False,
    "max_capture_points": 100,  # spending limit per attack
    "safety_buffer_seconds": 120  # don't convert if attack < 2 min away
}
```

**Key Features:**
- ✅ Time-aware conversion (calculates max crew that completes before attack)
- ✅ Respects spending limits (max capture points per attack)
- ✅ Safety buffer (won't convert if attack too close)
- ✅ Handles conversion-in-progress (won't start if one running)
- ✅ Dynamically fetches conversion parameters from API
- ✅ Accounts for base time penalty (startup cost)
- ✅ Manual mode available from menu (option 12.3)

**Example:**
```
Attack arrives in 600 seconds (10 minutes)
Safety buffer: 120 seconds
Available time: 480 seconds

Conversion data from API:
- Base time: 156 seconds (startup penalty)
- Time per crew: 7 seconds
- Points per crew: 10

Max crew by time:
  (480 - 156) / 7 = 46 crew points

Max crew by available points:
  250 capture points / 10 = 25 crew points

Actual conversion: min(46, 25) = 25 crew points
  Cost: 250 capture points
  Time: 156 + (25 * 7) = 331 seconds
  Completes: 269 seconds before attack (safe!)
```

**Commits:**
- `5082021` - Refactor: Move configuration to emergencyDefense module
- `8b27054` - Implement auto-pirate defense via crew conversion
- `b2d4885` - Update planning document with clarified requirements
- `d5bb9d8` - Add comprehensive planning document for auto-train defense feature

---

## Key Differences: Our Plan vs Implemented

### Feature #11 (Our Plan) vs Auto Crew Conversion (Implemented)

| Aspect | Feature #11 (Our Plan) | Auto Crew Conversion (Implemented) |
|--------|------------------------|-----------------------------------|
| **Approach** | Send pirate **missions** | Convert capture points to **crew** |
| **Mechanism** | Recruit pirates → send mission | Boost crew strength via conversion |
| **API Used** | Pirate fortress recruitment | Pirate fortress crew conversion |
| **Time Constraint** | Mission must complete before attack | Conversion must complete before attack |
| **Defense Type** | Active (pirates attack back) | Passive (crew strength boost) |
| **Capture Points** | Spent on mission cost | Spent on crew conversion |
| **Mission Duration** | 150s - 57600s (depends on mission) | 156s base + 7s per crew (dynamic) |
| **Configuration** | Not implemented yet | Fully implemented (menu option) |
| **Integration** | Planned for alertAttacksNG | Integrated into alertAttacks |
| **Manual Mode** | Not planned | Available (menu option 12.3) |
| **Status** | ❌ Not started | ✅ **FULLY WORKING** |

### Which Approach is Better?

**Crew Conversion (Implemented):**
- ✅ Simpler (one API call)
- ✅ Faster (shorter time penalty)
- ✅ More predictable (linear time calculation)
- ✅ Already working!
- ❌ Passive defense only (doesn't attack back)
- ❌ Limited by available capture points

**Pirate Missions (Our Plan):**
- ✅ Active defense (pirates fight back)
- ✅ Can use existing autoPirate.py logic
- ✅ Multiple mission options (different timings)
- ❌ More complex (captcha risk, mission selection)
- ❌ Longer minimum time (2m 30s vs dynamic)
- ❌ Not implemented yet

**User's Intent:** Need to clarify which approach they want!

---

## Architecture Comparison

### Current Planning (This Branch)

```
alertAttacksNG.py (NEW - standalone replacement)
  ├─ Dual-mode detection:
  │    ├─ Timer polling (5 min default)
  │    └─ Opportunistic (session.post interceptor)
  │
  ├─ Pirate classification (reuse from alertAttacks.py)
  │
  └─ Feature #11 integration (planned):
       └─ Auto-buy pirates (send missions)

attackMonitorState.py (NEW - state management)
  ├─ File-based state (~/.ikabot_attack_monitor_state.json)
  ├─ knownAttacks tracking
  └─ Cleanup old attacks (>24 hours)
```

**Status**: ❌ Not implemented (planning complete)

**Files to create**: 2 new files (~650 lines total)

**Upstream modifications**: 0 files (except menu - 2 lines)

---

### Implemented (Different Branch)

```
alertAttacks.py (MODIFIED - integrated defense)
  ├─ Pirate detection (same as our branch)
  ├─ Calls emergencyDefense.auto_defend_on_detection()
  └─ Formats and sends alert with defense result

emergencyDefense.py (NEW - dual-mode module)
  ├─ Manual mode (menu option 12.3)
  │    ├─ Scan for attacks
  │    ├─ User selects attack
  │    └─ Calls pirateDefense.auto_defend_pirate_attack()
  │
  ├─ Configuration interface
  │    └─ Stores in session data
  │
  └─ auto_defend_on_detection() (automatic mode)
       └─ Calls pirateDefense.auto_defend_pirate_attack()

pirateDefense.py (NEW - defense logic)
  ├─ get_pirate_fortress_city()
  ├─ get_conversion_data() (dynamic API fetch)
  ├─ calculate_max_crew_conversion() (time-aware)
  ├─ convert_crew_for_defense()
  ├─ auto_defend_pirate_attack() (main function)
  └─ format_defense_result()
```

**Status**: ✅ Fully implemented and working

**Files created**: 2 new files (~583 lines total)

**Upstream modifications**: 1 file (alertAttacks.py - added imports + call)

---

## Documentation Status

### On Current Branch

| Document | Status | Location | Notes |
|----------|--------|----------|-------|
| `feat-10-alertAttacksNG-architecture.md` | ✅ Complete | TEMP-PLANNING/ | 976 lines, ready to implement |
| `feat-11-auto-buy-pirates-on-detection.md` | ✅ Complete | TEMP-PLANNING/ | 542 lines, depends on #10 |
| `feat-10-parallel-attack-monitoring.md.old` | ⚠️ Archived | TEMP-PLANNING/ | Old approach (helper module), replaced by NG |

---

### On Documentation Branch

**Branch**: `origin/claude/analysis-and-documentation-011CUz15BfEZzx2rdz5LF9Mk`

| Document | Status | Topic |
|----------|--------|-------|
| `issue-04-alert-missing-pirate-classification.md` | ✅ Complete | Pirate detection problem analysis |
| `feat-09-alert-debug-logging.md` | ✅ Complete | Debug logging feature |
| `alertAttacks-flow-explained.md` | ✅ Complete | How alertAttacks works |
| (many others) | ✅ Complete | Various features/issues |

---

### On Auto-Train-Defense Branch

**Branch**: `origin/claude/auto-train-defense-01B2FzQ1cMSE1xLwvcXrRM1b`

| Document | Status | Notes |
|----------|--------|-------|
| `PLANNING-AUTO-TRAIN-DEFENSE.md` | ✅ Complete | 150+ lines, describes crew conversion approach |
| `feat-10-parallel-attack-monitoring.md` | ⚠️ OLD | Has old helper module approach, not NG |
| `feat-11-auto-buy-pirates-on-detection.md` | ⚠️ OLD | References militaryMonitor.py (old name) |

---

## What Should We Do Next? 🤔

### Option 1: Implement alertAttacksNG (Feature #10) as Planned

**Pros:**
- ✅ Follows current planning docs
- ✅ Dual-mode detection (timer + opportunistic)
- ✅ Zero modifications to upstream files (perfect for fork)
- ✅ Can integrate EITHER crew conversion OR pirate missions later

**Cons:**
- ❌ Doesn't leverage existing crew conversion implementation
- ❌ More work (creating new standalone process)

**Steps:**
1. Implement alertAttacksNG.py (400-500 lines)
2. Implement attackMonitorState.py (150 lines)
3. Test dual-mode detection
4. Parallel test with alertAttacks
5. Then decide: integrate crew conversion OR implement pirate missions

---

### Option 2: Merge Crew Conversion Defense to This Branch

**Pros:**
- ✅ Reuses working implementation from other branch
- ✅ Gets automatic pirate defense NOW
- ✅ Less work (just merge + test)
- ✅ Already has manual mode (menu option)

**Cons:**
- ❌ Doesn't get dual-mode detection (opportunistic)
- ❌ Modifies alertAttacks.py (merge conflict risk with upstream)
- ❌ Doesn't follow current planning docs

**Steps:**
1. Merge commits from auto-train-defense branch
2. Test crew conversion defense
3. Optionally: Implement alertAttacksNG later for dual-mode detection
4. Integrate crew conversion into alertAttacksNG (if implemented)

---

### Option 3: Hybrid Approach (Recommended?)

**Combine both:**
1. **First**: Merge crew conversion defense (get automatic defense NOW)
2. **Then**: Implement alertAttacksNG (get dual-mode detection)
3. **Finally**: Refactor crew conversion to integrate with alertAttacksNG

**Pros:**
- ✅ Immediate benefit (crew conversion working)
- ✅ Long-term benefit (dual-mode detection)
- ✅ Can test crew conversion thoroughly before refactoring
- ✅ Clean migration path

**Cons:**
- ❌ Most work (implement everything)
- ❌ Temporary duplication (crew conversion in alertAttacks, then move to NG)

**Steps:**
1. Merge crew conversion from auto-train-defense branch
2. Test and verify working
3. Implement alertAttacksNG.py (dual-mode detection)
4. Extract crew conversion logic to helper module
5. Call from both alertAttacks AND alertAttacksNG (during transition)
6. Eventually deprecate alertAttacks, keep only alertAttacksNG

---

### Option 4: Implement Pirate Missions (Feature #11 as Planned)

**Ignore crew conversion, implement Feature #11:**

**Pros:**
- ✅ Follows current planning docs
- ✅ Active defense (pirates fight back)
- ✅ Can reuse autoPirate.py logic

**Cons:**
- ❌ More complex (mission selection, captcha risk)
- ❌ Crew conversion already working on other branch
- ❌ Might be redundant if crew conversion sufficient

**Steps:**
1. Implement alertAttacksNG.py first (Feature #10)
2. Implement pirate mission logic (Feature #11)
3. Test mission selection and timing
4. Compare effectiveness vs crew conversion

---

## Questions to Answer

1. **Which defense mechanism do you prefer?**
   - Crew conversion (passive boost, simpler, working)
   - Pirate missions (active defense, more complex)
   - Both (use crew conversion for close attacks, missions for far attacks)?

2. **Should we merge the crew conversion implementation from the other branch?**
   - Yes → Get working defense immediately
   - No → Implement from scratch based on our plans

3. **Do we still want alertAttacksNG (dual-mode detection)?**
   - Yes → Faster detection via opportunistic checks
   - No → Keep using alertAttacks with integrated defense

4. **What's the priority order?**
   - A) Dual-mode detection first, defense later
   - B) Defense first (merge crew conversion), dual-mode later
   - C) Both in parallel
   - D) Something else

5. **For the fork maintenance strategy:**
   - Keep alertAttacks + add alertAttacksNG (parallel)?
   - Replace alertAttacks with alertAttacksNG?
   - Keep alertAttacks with integrated defense (like auto-train branch)?

---

## Recommendation

Based on analysis, I recommend **Option 3 (Hybrid Approach)**:

1. **Phase 1 (Week 1)**: Merge crew conversion defense from auto-train-defense branch
   - Immediate automatic pirate defense
   - Proven working implementation
   - Manual mode available (menu option)
   - Low risk (already tested)

2. **Phase 2 (Week 2-3)**: Implement alertAttacksNG with dual-mode detection
   - Faster attack detection (timer + opportunistic)
   - Zero upstream file modifications (perfect for fork)
   - Can run parallel with alertAttacks (testing phase)

3. **Phase 3 (Week 4)**: Refactor crew conversion to integrate with alertAttacksNG
   - Extract pirateDefense.py logic (already modular)
   - Add crew conversion call to alertAttacksNG detection logic
   - Remove from alertAttacks (deprecate alertAttacks)

4. **Phase 4 (Later)**: Optionally add pirate missions as alternative defense
   - Use crew conversion for close attacks (< 5 min)
   - Use pirate missions for far attacks (> 10 min)
   - User configurable preference

**Why this order:**
- ✅ Immediate value (working defense)
- ✅ Long-term value (dual-mode detection)
- ✅ Fork-friendly (eventually zero upstream modifications)
- ✅ Low risk (proven implementations)
- ✅ Modular (can stop after any phase)

---

## Next Steps (Awaiting Decision)

**Waiting for clarification on:**
1. Which defense mechanism to use (crew conversion vs pirate missions)
2. Whether to merge from auto-train-defense branch
3. Whether to implement alertAttacksNG
4. Priority order

**Once decided, ready to:**
- Merge crew conversion implementation (if chosen)
- Implement alertAttacksNG.py (if chosen)
- Implement pirate mission defense (if chosen)
- Update planning docs based on decision

---

**Branch Summary:**

| Branch | Pirate Detection | Defense | Dual-Mode Detection | Planning Docs |
|--------|-----------------|---------|---------------------|---------------|
| **Current** (`bug-pirate-not-classified`) | ✅ Done | ❌ None | ❌ None | ✅ NG architecture |
| **Auto-Train** (`auto-train-defense`) | ✅ Done | ✅ **Crew conversion** | ❌ None | ✅ Crew conversion plan |
| **Documentation** (`analysis-and-documentation`) | ✅ Analyzed | ❌ None | ❌ None | ✅ Analysis docs |

**Current state**: We have **pirate detection** working, and **two different approaches** to automatic defense:
- One **implemented** (crew conversion)
- One **planned** (pirate missions + dual-mode detection)

Need to decide which path forward!
