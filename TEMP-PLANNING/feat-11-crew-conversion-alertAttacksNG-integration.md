# Feature #11: Auto-Defense via Crew Conversion (alertAttacksNG Integration)

**Status**: PARTIAL - Crew conversion DONE, alertAttacksNG integration PENDING
**Priority**: MEDIUM (crew conversion already working in alertAttacks)
**Difficulty**: 2/10 (mostly refactoring existing code)
**Type**: Integration/Refactor
**Branch**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`

---

## Executive Summary

**What**: Integrate existing crew conversion defense into alertAttacksNG when it's implemented.

**Current State**:
- ✅ Crew conversion defense **FULLY WORKING** in alertAttacks.py
- ✅ Automatic mode (triggers on pirate detection)
- ✅ Manual mode (menu option 12.3)
- ❌ alertAttacksNG not implemented yet (Feature #10)

**Future State**:
- ✅ Crew conversion defense works in alertAttacksNG
- ✅ Dual-mode detection (timer + opportunistic) triggers crew conversion
- ✅ Same defense logic, faster detection
- ⚠️ Both alertAttacks + alertAttacksNG will coexist for some time

**Why this order**: Crew conversion already working, just needs to be called from alertAttacksNG when it exists.

---

## What's Already Implemented (Current Branch)

### ✅ Crew Conversion Defense

**Files created:**
- `ikabot/helpers/pirateDefense.py` (372 lines) - Defense logic
- `ikabot/function/emergencyDefense.py` (208 lines) - Dual-mode module

**Files modified:**
- `ikabot/function/alertAttacks.py` (~15 lines) - Triggers auto-defense
- `ikabot/command_line.py` (4 lines) - Adds menu option

**What it does:**
```
Pirate attack detected → Convert capture points → Crew strength
```

**How it works:**
1. Pirate attack detected (e.g., arrives in 600 seconds)
2. Fetch pirate fortress conversion data from API:
   - Base time: 156 seconds
   - Time per crew: 7 seconds
   - Points per crew: 10 capture points
3. Calculate max crew that completes before attack:
   - Available time: 600 - 120 (safety buffer) = 480 sec
   - Subtract base: 480 - 156 = 324 sec
   - Max crew: 324 / 7 = 46 crew points
4. Check spending limit:
   - User max: 200 capture points
   - Max by points: 200 / 10 = 20 crew points
5. Convert: min(46, 20) = 20 crew points
6. Conversion completes in 296 seconds (before attack!)
7. Alert user with result

**Configuration** (stored in session data):
```python
session_data["auto_pirate_defense"] = {
    "enabled": True/False,
    "max_capture_points": 200,  # spending limit per attack
    "safety_buffer_seconds": 120  # don't convert if attack < 2 min away
}
```

**Configured via**: Menu → 12 (Military) → 3 (Emergency Pirate Defense) → 2 (Configure)

---

## Integration with alertAttacksNG (Future - Feature #10)

### When Feature #10 is Implemented

**Current flow** (alertAttacks.py):
```python
# In alertAttacks.py do_it() function:
if isPirate and event_id not in knownAttacks:
    # ... build alert message ...

    # Trigger crew conversion defense
    try:
        from ikabot.function.emergencyDefense import auto_defend_on_detection
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

    sendToBot(session, msg)
```

**Future flow** (alertAttacksNG.py):
```python
# In alertAttacksNG.py check_for_attacks() function:
if isPirate and event_id not in state.known_attacks:
    # ... build alert message ...

    # Trigger crew conversion defense (SAME CODE!)
    try:
        from ikabot.function.emergencyDefense import auto_defend_on_detection
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

    sendToBot(session, msg)
```

**Integration effort**: Copy ~15 lines from alertAttacks.py to alertAttacksNG.py

---

## Why Crew Conversion (Not Pirate Missions)

**User clarification**: "crew conversion is what we needed (missions are not for this at all)"

### Crew Conversion Advantages:

1. **Simpler**:
   - One API call (conversion)
   - No mission selection logic
   - No captcha risk

2. **Faster**:
   - Predictable timing (156s base + 7s per crew)
   - vs missions (150s - 57600s depending on level)

3. **More reliable**:
   - Direct defense boost
   - No mission return timing to calculate
   - No risk of mission failure

4. **Already working**:
   - Fully implemented and tested
   - Used in production
   - Just needs to be called from alertAttacksNG

### vs Pirate Missions (Rejected):

| Aspect | Crew Conversion | Pirate Missions |
|--------|----------------|-----------------|
| **Mechanism** | Convert points → crew | Send pirates on mission |
| **Defense** | Passive (crew boost) | Active (pirates fight) |
| **Complexity** | Simple | Complex (mission selection) |
| **Captcha Risk** | None | High (mission sending) |
| **Timing** | Predictable (linear) | Variable (mission dependent) |
| **Status** | ✅ Working | ❌ Not needed |

---

## Coexistence Strategy

### Why Both Will Coexist

**User note**: "NG version will coexist with this one for some time"

**Reasons**:
1. **Opportunistic checks harder**: More complex to implement/test
2. **Risk mitigation**: Keep working alertAttacks while testing NG
3. **User choice**: Some may prefer simpler alertAttacks
4. **Gradual migration**: Build confidence in NG before switching

### Coexistence Plan

**Phase 1: alertAttacks Only (Current)**
```
alertAttacks.py:
  - Timer polling (user configured)
  - Crew conversion defense ✅
  - Proven stable
```

**Phase 2: Both Running (Future)**
```
alertAttacks.py:                  alertAttacksNG.py:
  - Timer polling                   - Timer polling (faster)
  - Crew conversion defense         - Opportunistic detection
  - Stable fallback                 - Crew conversion defense
                                    - Testing/validation

Both detect same attacks → both trigger defense
First to detect wins (idempotent - conversion won't run twice)
```

**Phase 3: NG Primary (Later)**
```
alertAttacksNG.py:
  - Dual-mode detection (timer + opportunistic)
  - Crew conversion defense
  - Primary recommendation

alertAttacks.py:
  - Still available (deprecated warning)
  - For users who prefer simplicity
```

**Phase 4: NG Only (Much Later)**
```
alertAttacksNG.py:
  - Only option
  - Fully proven

alertAttacks.py:
  - Removed (or kept for compatibility if low cost)
```

---

## Implementation Steps (When Feature #10 Done)

### Step 1: Add crew conversion to alertAttacksNG

**File**: `ikabot/function/alertAttacksNG.py`

**Add to pirate detection logic:**
```python
# In check_for_attacks() function
if isPirate:
    msg = "-- PIRATE ATTACK --\n"
    msg += missionText + "\n"
    msg += "from the pirate fortress {} of {}\n".format(origin["name"], origin["avatarName"])
    msg += "to {}\n".format(target["name"])
    msg += "arrival in: {}\n".format(daysHoursMinutes(timeLeft))
    msg += "(Pirate attacks cannot show unit/fleet numbers)\n"

    # NEW: Trigger crew conversion defense
    try:
        from ikabot.function.emergencyDefense import auto_defend_on_detection
        from ikabot.helpers.pirateDefense import format_defense_result

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

    sendToBot(session, msg)
```

**Lines added**: ~20 lines

---

### Step 2: Test dual-process scenario

**Run both processes:**
```bash
# Terminal 1
ikabot → (1) Alert if attacked (alertAttacks)

# Terminal 2
ikabot → (1.1) Alert Attacks NG (alertAttacksNG)
```

**Expected behavior:**
- Both detect same pirate attack
- Both attempt crew conversion
- First one wins (conversion already in progress for second)
- User gets 2 alerts (one success, one "already in progress")

**Verify:**
- No race conditions
- No duplicate conversions
- Both processes stable

---

### Step 3: Monitor and validate

**Track for 1-2 weeks:**
- Which process detects first (timer vs opportunistic)?
- Any missed detections?
- Any errors in NG version?
- User preference?

**Success criteria:**
- alertAttacksNG detects >= same attacks as alertAttacks
- Crew conversion works in both
- No crashes or errors
- User comfortable with NG

---

## Files Modified Summary

### Current State (Crew Conversion Already Merged):

| File | Status | Lines | Notes |
|------|--------|-------|-------|
| `ikabot/helpers/pirateDefense.py` | ✅ Created | 372 | Core defense logic |
| `ikabot/function/emergencyDefense.py` | ✅ Created | 208 | Dual-mode interface |
| `ikabot/function/alertAttacks.py` | ✅ Modified | +15 | Triggers defense |
| `ikabot/command_line.py` | ✅ Modified | +4 | Menu option |

**Total**: 2 new files (580 lines), 2 modified files (19 lines added)

---

### Future State (When Feature #10 Done):

| File | Status | Lines | Notes |
|------|--------|-------|-------|
| `ikabot/function/alertAttacksNG.py` | ⏳ Create | +20 | Copy defense trigger from alertAttacks |
| Everything else | ✅ Done | 0 | No changes needed! |

**Total additional**: ~20 lines in alertAttacksNG.py

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Crew conversion already working | N/A | N/A | ✅ Already done! |
| Integration with NG breaks defense | Low | Medium | Copy exact code from alertAttacks |
| Dual-process race conditions | Low | Low | Conversion API handles concurrent calls |
| User confusion (two processes) | Medium | Low | Clear documentation, migration plan |
| NG opportunistic harder than expected | Medium | Low | Keep alertAttacks working, migrate slowly |

**Overall Risk**: VERY LOW (crew conversion proven, integration is simple copy)

---

## Testing Plan

### Current Testing (Crew Conversion):
- ✅ Pirate attack detected
- ✅ Conversion triggered
- ✅ Timing calculated correctly
- ✅ Conversion completes before attack
- ✅ User alerted with result
- ✅ Manual mode works (menu option)
- ✅ Configuration persists (session data)

### Future Testing (alertAttacksNG Integration):
1. **Basic integration**:
   - NG detects pirate attack
   - Triggers crew conversion
   - Conversion succeeds
   - Alert sent with result

2. **Dual-process**:
   - Both alertAttacks + NG running
   - Pirate attack arrives
   - Both detect attack
   - Only one conversion executes
   - Both send alerts

3. **Opportunistic detection**:
   - NG running (20 min timer)
   - User runs shipMovements (opportunistic trigger)
   - Pirate attack in data
   - NG detects instantly (not waiting for timer)
   - Crew conversion triggered
   - Faster than alertAttacks could have been

4. **Edge cases**:
   - Attack too close (< safety buffer)
   - No capture points available
   - Conversion already in progress
   - No pirate fortress
   - API error during conversion

---

## Success Criteria

**Phase 1 (Current - DONE)**: ✅
- [x] Crew conversion implemented
- [x] Works in alertAttacks
- [x] Manual mode available
- [x] Configuration interface
- [x] Tested and stable

**Phase 2 (Feature #10 integration - PENDING)**:
- [ ] alertAttacksNG implemented (Feature #10)
- [ ] Crew conversion integrated into NG
- [ ] Works with dual-mode detection
- [ ] Both processes can coexist safely

**Phase 3 (Migration - FUTURE)**:
- [ ] User tests both for 1-2 weeks
- [ ] NG proven faster (opportunistic detection)
- [ ] NG proven stable (no crashes)
- [ ] User switches to NG as primary
- [ ] alertAttacks kept as fallback

---

## Documentation Notes

### Why This Document Exists

**User feedback**: "add docs so the misunderstanding we have here won't happen again (it should have been like in the other branch)"

**Misunderstanding**:
- Planning docs said "pirate missions" (Feature #11)
- Implementation used "crew conversion" (different branch)
- User clarified: crew conversion is correct approach

**Lesson learned**:
- Document what's IMPLEMENTED, not just planned
- Keep planning docs in sync with implementation
- Mark obsolete approaches clearly
- Cross-reference between branches

**This document**:
- ✅ Describes crew conversion (what's implemented)
- ✅ Explains why (not pirate missions)
- ✅ Integration plan with alertAttacksNG
- ✅ Coexistence strategy
- ✅ Clear status (DONE vs PENDING)

---

## Dependencies

**Required before starting Feature #11 integration:**
- ✅ Pirate detection working (DONE - current branch)
- ✅ Crew conversion implemented (DONE - current branch)
- ❌ alertAttacksNG implemented (PENDING - Feature #10)

**Blocks:**
- Nothing (crew conversion already working in alertAttacks)
- alertAttacksNG integration can happen anytime after Feature #10 done

---

## Summary

**Current state**:
- ✅ Crew conversion defense **FULLY WORKING**
- ✅ Integrated into alertAttacks.py
- ✅ Manual mode available (menu 12.3)
- ✅ Configuration interface
- ✅ Tested and stable

**Next steps**:
1. Implement Feature #10 (alertAttacksNG with dual-mode detection)
2. Copy crew conversion trigger code from alertAttacks to alertAttacksNG (~20 lines)
3. Test both processes running together
4. Gradually migrate users to alertAttacksNG
5. Keep alertAttacks as fallback during transition

**Why crew conversion**:
- Simpler, faster, more reliable than pirate missions
- Already working and proven
- Just needs to be called from alertAttacksNG
- User confirmed this is the correct approach

**Coexistence period**:
- Both alertAttacks + alertAttacksNG will run together for a while
- Opportunistic checks are harder to implement/test
- Low risk: both trigger same defense, API handles concurrency
- User can choose which to use during testing

---

**Created**: 2025-11-15
**Status**: Crew conversion DONE, alertAttacksNG integration PENDING (waiting for Feature #10)
**Branch**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`
