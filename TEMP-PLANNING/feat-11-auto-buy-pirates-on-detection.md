# Feature #11: Auto-Buy Pirates on Detection (Emergency Response)

**Status**: Planning - Overview Complete
**Priority**: MEDIUM (implements after Feature #10)
**Difficulty**: 2/10
**Type**: Feature Enhancement
**Branch**: TBD (will create after Feature #10 complete)

---

## Problem Statement

**Current situation:**
- Pirate attacks are now reliably detected (✅ DONE)
- User receives Telegram alert when pirate incoming
- User must manually respond: open game → find pirate fortress → buy pirates

**The problem:**
- Manual response takes time (5-15 minutes typically)
- User might be AFK (sleeping, working, etc.)
- Pirate attack arrives unchallenged → loses resources
- Existing `autoPirate.py` can recruit pirates, but not in emergency mode

**Example missed opportunity:**
```
14:00 - Pirate attack detected, arrives in 30 minutes
14:05 - User gets alert, but is in meeting
14:20 - User finally opens game
14:25 - Buys pirates, sends fastest mission (2m 30s)
14:27:30 - Pirates return
14:30 - Pirate attack arrives (2m 30s gap = still vulnerable!)
```

**If automated:**
```
14:00 - Pirate attack detected, auto-buy triggers instantly
14:02:30 - Pirates return (27m 30s before attack!)
14:30 - Pirate attack arrives (safely defended)
```

---

## Solution Overview

**Add emergency pirate recruitment to centralized attack detection:**

```
┌─────────────────────────────────────────────────────┐
│  ikabot/helpers/militaryMonitor.py                  │
│                                                      │
│  def check_for_attacks(...):                        │
│    - Classify pirate vs player                      │
│    - Send alert                                     │
│                                                      │
│    NEW: Emergency Response                          │
│    - If pirate detected:                            │
│      1. Get time until arrival                      │
│      2. Find city with pirate fortress              │
│      3. Select fastest mission that completes       │
│         before attack arrives                       │
│      4. Respect spending limit config               │
│      5. Buy and send pirates                        │
│      6. Alert user of action taken                  │
└─────────────────────────────────────────────────────┘
```

**Result:** Instant automated response to pirate attacks, maximizes defense time.

---

## Implementation Plan (HIGH LEVEL)

### Phase 1: Configuration

**File:** `ikabot/config.py` (existing file)

**Add new config options:**
```python
# Auto-buy pirates on detection
AUTO_BUY_PIRATES_ENABLED = False  # Must be explicitly enabled by user
AUTO_BUY_PIRATES_MAX_POINTS = 100  # Maximum capture points to spend per attack
AUTO_BUY_PIRATES_BUFFER_MINUTES = 5  # Safety buffer (don't buy if attack < 5 min away)
```

**User configuration:**
- Add prompt to `alertAttacks.py` setup
- Ask: "Auto-buy pirates on detection? (y/N)"
- If yes: "Maximum capture points to spend per attack? (default: 100)"
- If yes: "Safety buffer in minutes? (default: 5)"
- Store in session data (like existing alertAttacks config)

---

### Phase 2: Emergency Recruitment Function

**File:** `ikabot/helpers/militaryMonitor.py` (modified from Feature #10)

**Add new function:**
```python
def emergency_recruit_pirates(session, attack_arrival_seconds, target_city_id):
    """
    Automatically recruit and send pirates in response to detected attack.

    Parameters:
    - session: session object
    - attack_arrival_seconds: seconds until attack arrives
    - target_city_id: city being attacked

    Returns:
    - dict with recruitment result (success/failure, points spent, mission sent)
    """
    # 1. Check if auto-buy enabled in config
    # 2. Find cities with pirate fortress (reuse from autoPirate.py)
    # 3. Select fastest mission that completes before attack
    # 4. Check capture points available
    # 5. Respect spending limit
    # 6. Buy and send pirates
    # 7. Return result for logging/alerting
```

**Mission Selection Logic:**
```python
def select_emergency_mission(attack_arrival_seconds, buffer_minutes=5):
    """
    Select fastest pirate mission that completes before attack arrives.

    Returns: mission_choice (1-9) or None if no mission fits
    """
    # piracyMissionWaitingTime from config.py:
    # {1: 150s (2m30s), 2: 450s (7m30s), 3: 900s (15m), ...}

    buffer_seconds = buffer_minutes * 60
    available_time = attack_arrival_seconds - buffer_seconds

    # Find fastest mission that completes in time
    for mission_id in sorted(piracyMissionWaitingTime.keys()):
        if piracyMissionWaitingTime[mission_id] <= available_time:
            return mission_id

    return None  # No mission completes in time
```

---

### Phase 3: Integration with Attack Detection

**File:** `ikabot/helpers/militaryMonitor.py` (modified)

**Modify `check_for_attacks()` function:**
```python
def check_for_attacks(movements, time_now, postdata, session, city_id):
    # ... existing detection logic ...

    # For each NEW pirate attack detected:
    if isPirate and event_id not in knownAttacks:
        # ... existing alert logic ...

        # NEW: Emergency recruitment
        if config.AUTO_BUY_PIRATES_ENABLED:
            try:
                result = emergency_recruit_pirates(
                    session,
                    timeLeft,  # seconds until arrival
                    target["id"]  # city being attacked
                )

                if result["success"]:
                    # Alert user of automated response
                    msg = "\n--- AUTOMATED RESPONSE ---\n"
                    msg += "Recruited pirates: {} mission\n".format(result["mission_name"])
                    msg += "Capture points spent: {}\n".format(result["points_spent"])
                    msg += "Pirates return in: {}\n".format(daysHoursMinutes(result["return_time"]))
                    sendToBot(session, msg)
                else:
                    # Alert user of failure
                    msg = "\n--- AUTO-BUY FAILED ---\n"
                    msg += "Reason: {}\n".format(result["reason"])
                    sendToBot(session, msg)
            except Exception as e:
                # Don't let emergency response break detection
                msg = "Emergency pirate recruitment failed: {}\n".format(str(e))
                sendToBot(session, msg)
```

---

### Phase 4: Reuse Existing Code

**From `autoPirate.py` (lines 320-343):**
```python
def getPiracyCities(session, pirateMissionChoice):
    """Gets all user's cities which have a pirate fortress"""
    # Already implemented, can import and reuse
    # Returns: list of cities with fortress at required level
```

**From `autoPirate.py` (lines 346-387):**
```python
def convertCapturePoints(session, piracyCities, convertPerMission):
    """Converts capture points into crew strength"""
    # Already handles spending limits ("all" or specific amount)
    # Can reuse for emergency conversions
```

**Key difference from `autoPirate.py`:**
- `autoPirate.py`: Runs N missions on schedule, solves captchas
- Emergency mode: Runs ONCE per attack, **MUST avoid captcha** (no time for solving)
- Strategy: Keep crew strength HIGH proactively, emergency just sends existing crew

---

## Files Modified Summary (Feature 1)

| File | Type | Changes | Risk |
|------|------|---------|------|
| `ikabot/helpers/militaryMonitor.py` | MODIFY | +~100 lines (emergency logic) | LOW |
| `ikabot/config.py` | MODIFY | +3 lines (config options) | VERY LOW |
| `ikabot/function/alertAttacks.py` | MODIFY | +~15 lines (setup prompts) | VERY LOW |

**Total:**
- 0 new files (adds to Feature #10's file)
- 3 modified files
- ~120 new lines total
- Merge conflict risk: **VERY LOW** (minimal changes, mostly to new file)

---

## Benefits of Feature 1

### Immediate Benefits:
1. **Instant response** - no waiting for user to be available
2. **Maximized defense time** - pirates recruited immediately
3. **User convenience** - automated defense, user just gets notification
4. **Configurable limits** - spending cap prevents runaway costs

### Example Speed Improvement:
**Before (manual):**
- Attack detected at 14:00, arrives in 30 minutes
- User responds at 14:20 (20 min late)
- Buys pirates, mission completes at 14:22:30
- Defense active for 7 min 30 sec before attack

**After (automated):**
- Attack detected at 14:00, auto-buy instant
- Pirates sent at 14:00:05 (5 sec delay)
- Mission completes at 14:02:35
- Defense active for 27 min 25 sec before attack (3.6x longer!)

### Risk Mitigation:
- **Spending limit** prevents excessive capture point usage
- **Safety buffer** prevents buying if attack too close (no time for mission)
- **Failure alerts** notify user if auto-buy fails
- **Manual override** user can disable entirely

---

## Configuration Strategy

### Setup Flow (in `alertAttacks.py`):
```python
def alertAttacks(session, event, stdin_fd, predetermined_input):
    # ... existing polling interval setup ...

    print("Do you want to automatically recruit pirates when attacks are detected? (y/N)")
    auto_buy = read(values=["y", "Y", "n", "N", ""])

    if auto_buy.lower() == "y":
        print("Maximum capture points to spend per attack? (min: 10, default: 100)")
        max_points = read(min=10, digit=True, default=100)

        print("Safety buffer in minutes (don't buy if attack closer than this)? (default: 5)")
        buffer = read(min=0, digit=True, default=5)

        # Store in session for use by militaryMonitor
        session_data = session.getSessionData()
        session_data["auto_pirate"] = {
            "enabled": True,
            "max_points": max_points,
            "buffer_minutes": buffer
        }
        session.setSessionData(session_data)
    else:
        # Ensure disabled
        session_data = session.getSessionData()
        session_data["auto_pirate"] = {"enabled": False}
        session.setSessionData(session_data)
```

**Why session data?**
- Persists across restarts
- Available to militaryMonitor.py (shared state)
- User can reconfigure by restarting alertAttacks

---

## Testing Plan

### Test Cases:

1. **Basic auto-buy (30 min advance notice)**
   - Enable auto-buy, max 100 points
   - Trigger pirate attack arriving in 30 minutes
   - Verify fastest mission selected (2m 30s)
   - Verify pirates sent automatically
   - Verify alert message includes mission details

2. **Spending limit enforcement**
   - Set max 50 points
   - Trigger attack with only 40 points available
   - Verify mission sent
   - Trigger attack with 0 points available
   - Verify failure alert, no mission sent

3. **Safety buffer**
   - Set buffer to 5 minutes
   - Trigger attack arriving in 4 minutes
   - Verify NO mission sent (too close)
   - Verify alert explains why (safety buffer)

4. **Mission selection logic**
   - Attack in 3 minutes → mission 1 (2m 30s)
   - Attack in 10 minutes → mission 2 (7m 30s)
   - Attack in 20 minutes → mission 3 (15m)
   - Verify correct mission chosen each time

5. **No pirate fortress**
   - Enable auto-buy
   - Trigger attack on account with no fortress
   - Verify failure alert
   - Verify no crash

6. **Disabled auto-buy**
   - Disable feature in setup
   - Trigger pirate attack
   - Verify regular alert sent
   - Verify NO auto-buy attempt

7. **Normal player attack (not pirate)**
   - Enable auto-buy
   - Trigger normal player attack
   - Verify NO auto-buy triggered
   - Verify regular alert sent with vacation mode option

8. **Fortress too low level**
   - Enable auto-buy
   - Trigger attack requiring mission 3 (15m)
   - User only has level 1 fortress (max mission 1)
   - Verify fallback to mission 1 or failure alert

---

## Technical Details to Investigate (Phase 2 Deep Dive)

### Questions to Answer:

1. **Captcha avoidance:**
   - How often do pirate missions trigger captcha?
   - Can we pre-send missions proactively to avoid captcha?
   - What happens if captcha triggered during emergency?
   - Fallback strategy?

2. **Capture points checking:**
   - Where to fetch current capture points?
   - Same API as `autoPirate.py`? (line 365)
   - How to handle conversion in progress?

3. **Crew strength:**
   - Do we need to check current crew strength?
   - What if crew at 0? (mission fails)
   - Should we auto-convert points to crew?

4. **Multiple attacks:**
   - What if 2 pirate attacks on different cities simultaneously?
   - Spend limit per attack or total?
   - Alert user of multiple attacks?

5. **Pirate fortress location:**
   - If attack on city A, fortress in city B
   - Pirates from B defend A? (verify game mechanics)
   - Or do we need fortress in same city?

6. **Error handling:**
   - What if fortress destroyed between detection and response?
   - What if capture mission already in progress?
   - What if API call fails?

7. **Race conditions:**
   - User manually buys pirates SAME TIME as auto-buy
   - How to detect and prevent double-spending?
   - File locking needed?

8. **Testing without real attacks:**
   - How to simulate pirate attack for testing?
   - Mock API responses?
   - Test mode flag?

---

## Dependencies

**Required before starting:**
- Feature #10 (parallel monitoring) COMPLETE (✅ foundation)
- `militaryMonitor.py` exists and working (✅ from Feature #10)
- Pirate detection reliable (✅ DONE)
- Understanding of pirate fortress mechanics (⏳ NEEDS INVESTIGATION)

**Blocks:**
- Nothing (this is final feature in sequence)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Spending runaway | Low | Medium | Spending limit config, per-attack tracking |
| Captcha triggered | Medium | High | Pre-send missions, maintain crew proactively |
| No fortress available | Low | Low | Clear failure alert, graceful degradation |
| API call failure | Low | Medium | Try-catch, alert user, don't break detection |
| User confusion | Medium | Low | Clear setup prompts, detailed alerts |
| Game mechanics misunderstanding | Medium | High | Thorough investigation, test with real attacks |

**Overall Risk:** LOW

---

## Integration with Feature #10

**Feature #10 provides foundation:**
- Centralized `militaryMonitor.py` file
- Pirate detection logic
- Alert messaging system
- Debug logging (if kept)

**Feature #11 adds on top:**
- Emergency response function
- Configuration options
- Mission selection logic
- Spending tracking

**Clean separation:**
- Feature #10: **Detection** (when/what)
- Feature #11: **Response** (react/defend)

**Example call flow:**
```python
# In militaryMonitor.py check_for_attacks():

# Feature #10 code:
isPirate = (event.type == "piracy" and event.missionIconClass == "piracyRaid")
if isPirate:
    sendToBot(session, "-- PIRATE ATTACK --\n...")

    # Feature #11 addition (just 3 lines):
    if config.AUTO_BUY_PIRATES_ENABLED:
        result = emergency_recruit_pirates(session, timeLeft, target_city_id)
        sendToBot(session, format_recruitment_result(result))
```

---

## Alternatives Considered

### Alternative 1: Separate Module
**Approach:** Create new `autoBuyPirates.py` module that polls for attacks

**Rejected because:**
- Duplicates attack detection (Feature #10 already does this)
- More API calls (polling again)
- Higher merge conflict risk (another modified file)
- Misses fast detection from parallel monitoring

### Alternative 2: Extend autoPirate.py
**Approach:** Add emergency mode to existing `autoPirate.py`

**Rejected because:**
- `autoPirate.py` is scheduled missions (different use case)
- Would make file more complex (mixing concerns)
- Feature #10's `militaryMonitor.py` is better integration point

### Alternative 3: Manual Telegram Response
**Approach:** Send Telegram message with "buy pirates" option, user responds

**Rejected because:**
- Requires user to be available (defeats purpose)
- Slower response time (user reaction delay)
- Telegram API complexity (polling for responses)
- Already have this via "activate vacation mode" pattern

---

## Future Enhancements (Out of Scope)

1. **Machine learning mission selection:**
   - Analyze historical attack patterns
   - Predict optimal mission timing
   - Adjust based on success rate

2. **Crew strength auto-management:**
   - Proactively maintain crew at high level
   - Auto-convert points to crew on schedule
   - Ensure emergency missions always have crew

3. **Multi-fortress coordination:**
   - If multiple cities with fortresses
   - Send from all simultaneously
   - Maximize defense across all cities

4. **Cost tracking and reporting:**
   - Track total points spent on auto-defense
   - Weekly/monthly reports
   - ROI analysis (points spent vs resources saved)

5. **Smart captcha avoidance:**
   - Pre-send dummy missions periodically
   - Keep "pirate mission sent recently" flag active
   - Reduce captcha probability during emergency

---

**Created**: 2025-11-14
**Status**: Planning - Overview Complete
**Next**: Wait for Feature #10 completion, then investigate technical details
**Depends On**: Feature #10 (parallel monitoring) must be implemented first

---

## Summary

**What**: Automatically recruit and send pirates when attack detected
**Why**: Instant response, maximize defense time, user convenience
**How**: Add emergency logic to `militaryMonitor.py` from Feature #10
**Risk**: Low (small changes, configurable limits, clear failure handling)
**Benefit**: 3-4x longer defense window compared to manual response

**Key Success Criteria:**
- User can enable/disable with clear prompts
- Spending limit respected (no runaway costs)
- Correct mission selected (completes before attack)
- Clear alerts (user knows what happened)
- Graceful failures (doesn't break detection)

This feature transforms passive attack alerts into active automated defense.
