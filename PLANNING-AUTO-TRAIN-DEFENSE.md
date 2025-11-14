# Feature: Auto-Train Defense Units on Pirate Attack Detection

**Status**: Requirements Clarified - Ready for Implementation
**Priority**: HIGH
**Difficulty**: 7/10 (increased due to dual-mode requirement)
**Type**: Emergency Response Feature + Manual Command
**Branch**: `claude/auto-train-defense-01B2FzQ1cMSE1xLwvcXrRM1b`
**Based On**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7` (pirate detection)

---

## UPDATED REQUIREMENTS (from user feedback)

### Key Clarifications:
1. **Spending Limit**: Max resources per defense (similar to trainArmy), but **time constraint is primary rule**
2. **Unit Selection**: Follow pattern from how pirates are trained in autoPirate.py
3. **Safety Buffer**: Must be in **SECONDS** (not minutes)
   - Account for "process start time penalty"
   - User mentioned: "10 resources 10s = 1 pirate" (need to investigate exact meaning)
4. **Multiple Attacks**: Spending limit is **per attack** (not global)
5. **DUAL MODE OPERATION**:
   - **Automatic mode**: Triggered by alertAttacks when pirate detected
   - **Manual mode**: User can run as command from menu when they see an attack
   - Manual mode calculates and gives order to train (time-sensitive)
   - See: loadCustomModule or how to register modules in command_line.py

### Implementation Approach:
- Create standalone module that can be called in TWO ways:
  1. From alertAttacks.py (automatic trigger)
  2. From menu as "Emergency Defense Training" command (manual trigger)
- Register in menu under "Military actions" (12) as option (3) → becomes menu item 1203
- Module signature: `def emergencyDefense(session, event, stdin_fd, predetermined_input)`

---

## Executive Summary

**What**: Automatically train defensive military units when a pirate attack is detected, ensuring they complete training BEFORE the attack arrives.

**Why**: Currently, when a pirate attack is detected, users receive an alert but must manually train defense units. This feature automates the response, maximizing defense preparation time.

**Critical Constraint**: Units MUST be fully trained before the attack arrives. Training that won't complete in time should NOT be initiated.

**Key Innovation**: Time-aware training calculation - only train units that will complete before attack based on:
- Attack arrival time (from pirate detection)
- Unit training duration (from barracks data)
- Current training queue status
- Resource availability
- User-configured spending limits
- Process start time penalty (accounts for API call delays)

**Dual Operation Modes**:
1. **Automatic**: Triggered when alertAttacks detects pirate attack
2. **Manual**: User runs "Emergency Defense Training" from menu (option 12.3)
   - Scans for incoming attacks
   - Calculates optimal defense
   - Queues training with user confirmation

---

## Problem Statement

### Current Situation
From the pirate detection branch (`claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`):
- ✅ Pirate attacks reliably detected via `alertAttacks.py`
- ✅ User receives Telegram alert with time until arrival
- ✅ Attack type classified (pirate vs player)
- ❌ User must manually respond to train defenses

### The Problem
**Manual response workflow:**
```
14:00 - Pirate attack detected, arrives in 2 hours
14:05 - User receives Telegram alert
14:20 - User finally opens game (15 min delay)
14:25 - User queues unit training (5 min to decide)
14:30 - Training starts
15:30 - Training completes (1 hour duration)
16:00 - Attack arrives (defended ✓, but cut close)
```

**Risks with manual approach:**
- User AFK (sleeping, working, etc.) → no defense prepared
- User delays → training might not complete in time
- User misjudges timing → wastes resources on units that won't finish
- User over-spends → trains too many units

**If automated:**
```
14:00 - Pirate attack detected, arrives in 2 hours
14:00:05 - Auto-train triggers (instant response)
14:00:10 - Optimal units calculated and training queued
15:00:10 - Training completes
16:00 - Attack arrives (defended ✓, with 1 hour buffer)
```

**Benefits:**
- Instant response (no user delay)
- Optimal unit selection (fits within time window)
- Respects spending limits (controlled costs)
- Maximizes preparation time

---

## Solution Architecture

### High-Level Design (Dual-Mode Architecture)

```
MODE 1: AUTOMATIC (from alertAttacks)
┌─────────────────────────────────────────────────────────────────┐
│  ikabot/function/alertAttacks.py (MODIFY)                       │
│                                                                  │
│  When pirate attack detected:                                   │
│    1. Extract attack timing data (already done)                 │
│    2. If auto-train enabled:                                    │
│       - Import emergencyDefense module                          │
│       - Call auto_train_for_attack(session, attack_data)        │
│    3. Append result to alert notification                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
            ┌───────────────────────────────┐
            │  MODE 2: MANUAL (from menu)   │
            │                               │
            │  Menu: Military Actions (12)  │
            │  Option 3: Emergency Defense  │
            │  → Item 1203                  │
            └───────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ikabot/function/emergencyDefense.py (NEW MODULE)               │
│                                                                  │
│  def emergencyDefense(session, event, stdin_fd, ...):           │
│    - Banner & intro                                             │
│    - Fetch current military movements (API call)                │
│    - Scan for incoming attacks (hostile movements)              │
│    - Display attacks to user with timing                        │
│    - Ask user: "Train defense for which attack? (0 to cancel)"  │
│    - Call shared helper: auto_train_for_attack()                │
│    - Display result (what trained, when ready, etc.)            │
│                                                                  │
│  def auto_train_for_attack(session, attack_data):               │
│    - Shared function used by BOTH modes                         │
│    - Import from helpers.autoTrainDefense                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  ikabot/helpers/autoTrainDefense.py (NEW HELPER)                │
│                                                                  │
│  def calculate_and_train_defense(session, target_city_id,       │
│                                   attack_arrival_seconds,       │
│                                   max_resources, buffer_sec):   │
│    - Get target city data                                       │
│    - Check for barracks                                         │
│    - Get available units & training times                       │
│    - Calculate current training queue time                      │
│    - Account for safety buffer + process start penalty          │
│    - Select units that fit time window                          │
│    - Respect resource spending limit (primary: time constraint) │
│    - Queue training via trainArmy.train()                       │
│    - Return result dict (success, units, resources, timing)     │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. Configuration (User Settings)
Stored in session data (like existing features):
```python
session_data["auto_train_defense"] = {
    "enabled": True,
    "max_resource_value": 5000,  # Max total resource value to spend per attack
    "safety_buffer_seconds": 120,  # Don't train if attack < 120 sec away (accounts for process delays)
    "process_start_penalty": 30,  # Seconds to account for API calls and queue delays
    "preferred_units": ["phalanx", "swordsman"],  # Priority order (optional)
}
```

#### 2. Time Calculation Logic
**Critical calculation:**
```python
available_time = attack_arrival_seconds - (safety_buffer * 60)

# Account for existing training queue
current_queue_time = get_current_training_duration(session, city)
available_time -= current_queue_time

# For each unit type:
total_training_time = 0
for unit in units_to_train:
    unit_training_time = unit["completiontime"] * quantity
    total_training_time += unit_training_time

    if total_training_time > available_time:
        # STOP: This unit won't finish in time
        break
```

#### 3. Unit Selection Algorithm
**Priority order:**
1. **Time constraint** - MUST complete before attack
2. **Resource availability** - Can we afford it?
3. **Spending limit** - Within user's max budget?
4. **Unit effectiveness** - Prefer stronger units if time allows
5. **User preferences** - Use configured priority list

**Example:**
```
Attack arrives in: 3600 seconds (1 hour)
Safety buffer: 600 seconds (10 min)
Current queue: 0 seconds (no training in progress)
Available time: 3000 seconds (50 min)

Unit options:
- Phalanx: 71 sec each, can train 42 units (2982 sec total)
- Swordsman: 214 sec each, can train 14 units (2996 sec total)
- Archer: 107 sec each, can train 28 units (2996 sec total)

Resource check:
- Phalanx: 42 units * (27 wood + 30 sulfur) = 2394 resources
- Within limit? YES (< 5000)

Decision: Train 42 Phalanx units (completes in 49.7 min, attack in 60 min)
```

---

## Implementation Plan

### Phase 1: Core Auto-Train Module (NEW FILE)
**File**: `ikabot/helpers/autoTrainDefense.py`

**Functions needed:**
```python
def auto_train_defense(session, target_city_id, attack_arrival_seconds, config):
    """
    Main entry point - orchestrates auto-training response.
    Returns: dict with result (success/failure, units trained, etc.)
    """

def calculate_available_training_time(session, city, attack_arrival_seconds, buffer_seconds, process_penalty):
    """
    Calculate how much time available for training.
    Accounts for: attack arrival, safety buffer (seconds), process start penalty, existing queue.
    Returns: available_seconds (int)
    """

def get_trainable_units(session, city):
    """
    Fetch unit types available in barracks with training times.
    Reuses logic from trainArmy.py (getBuildingInfo, generateArmyData)
    Returns: list[dict] with unit data
    """

def select_optimal_units(units, available_time, available_resources, max_spend, preferences):
    """
    Select which units to train based on constraints.
    Returns: list[dict] of units to train with quantities
    """

def queue_training(session, city, training_plan):
    """
    Execute the training queue.
    Reuses logic from trainArmy.py (train function)
    Returns: success (bool)
    """
```

### Phase 2: Integration with Alert System
**File**: `ikabot/function/alertAttacks.py` (MODIFY)

**Changes needed** (minimal, ~15 lines):
```python
# In do_it() function, after pirate detection:

if isPirate and event_id not in knownAttacks:
    # ... existing alert message building ...

    # NEW: Auto-train defense
    session_data = session.getSessionData()
    auto_train_config = session_data.get("auto_train_defense", {})

    if auto_train_config.get("enabled", False):
        try:
            from ikabot.helpers import autoTrainDefense
            result = autoTrainDefense.auto_train_defense(
                session=session,
                target_city_id=target["id"],
                attack_arrival_seconds=timeLeft,
                config=auto_train_config
            )

            # Append result to alert message
            if result["success"]:
                msg += "\n--- AUTO-DEFENSE ACTIVATED ---\n"
                msg += f"Queued: {result['units_summary']}\n"
                msg += f"Training completes: {daysHoursMinutes(result['completion_time'])}\n"
                msg += f"Resources spent: {result['resources_spent']}\n"
            else:
                msg += f"\n--- AUTO-TRAIN FAILED ---\n{result['reason']}\n"
        except Exception as e:
            # Don't break alert system if auto-train fails
            msg += f"\n--- AUTO-TRAIN ERROR ---\n{str(e)}\n"

    sendToBot(session, msg)
```

### Phase 3: Configuration Setup
**File**: `ikabot/function/alertAttacks.py` (MODIFY)

**Add to setup prompts** (~30 lines):
```python
def alertAttacks(session, event, stdin_fd, predetermined_input):
    # ... existing polling interval setup ...

    print("\nAuto-train defense units when pirate attacks detected? (y/N)")
    auto_train = read(values=["y", "Y", "n", "N", ""])

    if auto_train.lower() == "y":
        print("Maximum resource value to spend per attack? (min: 100, default: 5000)")
        max_spend = read(min=100, digit=True, default=5000)

        print("Safety buffer in SECONDS (don't train if attack closer than this)? (default: 120)")
        print("Note: Accounts for API delays and training queue startup time")
        buffer_sec = read(min=0, digit=True, default=120)

        print("Preferred unit types (comma-separated, e.g., phalanx,swordsman):")
        print("Press enter for default (all units by strength)")
        pref_input = read(default="")
        preferred = [u.strip() for u in pref_input.split(",")] if pref_input else []

        # Store configuration
        session_data = session.getSessionData()
        session_data["auto_train_defense"] = {
            "enabled": True,
            "max_resource_value": max_spend,
            "safety_buffer_seconds": buffer_sec,
            "process_start_penalty": 30,  # Fixed 30 sec for API/queue delays
            "preferred_units": preferred
        }
        session.setSessionData(session_data)

        print(f"\n✓ Auto-train enabled: max {max_spend} resources, {buffer_sec} sec buffer")
    else:
        # Ensure disabled
        session_data = session.getSessionData()
        session_data["auto_train_defense"] = {"enabled": False}
        session.setSessionData(session_data)
```

---

## Code Reuse Strategy (Minimal Changes to Existing Files)

### From `trainArmy.py` (REUSE, don't modify):
```python
# Line 22-45: getBuildingInfo() - fetch barracks data
# Line 165-183: generateArmyData() - parse unit types
# Line 48-72: train() - queue training

# Strategy: Import these functions directly
from ikabot.function.trainArmy import getBuildingInfo, generateArmyData, train
```

### From `alertAttacks.py` (MINIMAL MODIFY):
- Current: ~166 lines
- Changes: +~50 lines (config prompts + auto-train call)
- Total: ~216 lines
- **Ratio**: Only 30% new code in existing file

### New Code (ISOLATED):
- `autoTrainDefense.py`: ~200-250 lines (NEW file)
- No changes to other modules

**Fork-friendly approach:**
- Only 1 existing file modified (`alertAttacks.py`)
- All new logic in separate helper file
- Easy to merge upstream changes (minimal conflicts)

---

## Key Technical Challenges

### Challenge 1: Accurate Time Calculation
**Problem**: Must account for existing training queue

**Solution**:
```python
# From trainArmy.py line 83-89:
def getCurrentTrainingDuration(session, city):
    """Get time remaining for current training queue."""
    data = getBuildingInfo(session, city, trainTroops=True)
    html = data[1][1][1]
    seconds = re.search(r"'buildProgress', (\d+),", html)
    if seconds:
        return int(seconds.group(1)) - data[0][1]["time"]
    return 0
```

**Risk**: LOW - existing code pattern works

---

### Challenge 2: Resource Limit Enforcement
**Problem**: User sets max resource VALUE, but units cost multiple resources

**Solution**:
```python
def calculate_resource_value(unit_costs, quantity):
    """Calculate total resource value (simplified: sum all resources)."""
    total = 0
    for resource in ["wood", "wine", "marble", "sulfur"]:
        if resource in unit_costs:
            total += unit_costs[resource] * quantity
    return total

# Alternative: Use market prices for accurate value
# But simple sum is good enough for spending limit
```

**Risk**: LOW - simple calculation

---

### Challenge 3: No Barracks in Target City
**Problem**: Attack targets city without barracks

**Solution**: Graceful failure
```python
if "barracks" not in city["position"]:
    return {
        "success": False,
        "reason": "Target city has no barracks - cannot train defense"
    }
```

**Alert message**: User notified, no crash

**Risk**: LOW - clear error handling

---

### Challenge 4: Insufficient Resources
**Problem**: Not enough resources to train optimal units

**Solution**: Train what we CAN afford (from `trainArmy.py` line 122-137)
```python
# Calculate limiting resource
for resource in materials:
    if resource in unit["costs"]:
        limiting = available_resources[resource] // unit["costs"][resource]
        units_to_train = min(units_to_train, limiting)
```

**Alert message**: "Trained 10/20 requested units (insufficient resources)"

**Risk**: LOW - existing code pattern

---

### Challenge 5: Multiple Simultaneous Attacks
**Problem**: 2 pirate attacks on different cities at same time

**Current approach**: Each attack triggers independently
- Attack 1 on City A → trains in City A
- Attack 2 on City B → trains in City B
- No resource conflict (different cities)

**Future enhancement** (out of scope): Global spending limit across all attacks

**Risk**: MEDIUM - edge case, but acceptable behavior

---

## Files Modified Summary (UPDATED for Dual-Mode)

| File | Type | Changes | Lines | Risk |
|------|------|---------|-------|------|
| `ikabot/function/emergencyDefense.py` | **NEW** | Standalone module (manual + auto modes) | ~300 | None (new file) |
| `ikabot/helpers/autoTrainDefense.py` | **NEW** | Core training logic (shared by both modes) | ~200 | None (new file) |
| `ikabot/command_line.py` | MODIFY | Add menu item 1203 "Emergency Defense" | +2 | VERY LOW |
| `ikabot/function/alertAttacks.py` | MODIFY | Config + auto-trigger call | +~50 | LOW (isolated additions) |

**Total:**
- 2 new files (module + helper)
- 2 modified files (menu + alertAttacks)
- ~550 new lines total
- **Fork merge risk**: VERY LOW (minimal changes to existing code, mostly new files)

---

## Configuration Example

### User Setup Flow
```
--- Alert Attacks Setup ---
How often should I search for attacks? (min:3, default: 20): 15

Auto-train defense units when pirate attacks detected? (y/N): y
Maximum resource value to spend per attack? (min: 100, default: 5000): 3000
Safety buffer in minutes (don't train if attack closer than this)? (default: 10): 15
Preferred unit types (comma-separated, e.g., phalanx,swordsman): phalanx

✓ Auto-train enabled: max 3000 resources, 15 min buffer
✓ I will check for attacks every 15 minutes
```

### Resulting Configuration
```json
{
  "auto_train_defense": {
    "enabled": true,
    "max_resource_value": 3000,
    "safety_buffer_minutes": 15,
    "preferred_units": ["phalanx"]
  }
}
```

---

## Alert Message Examples

### Success Case
```
-- PIRATE ATTACK --
Plundering raid
from the pirate fortress Pirate Haven of Captain Blackbeard
to Athens
arrival in: 1H 30M
(Pirate attacks cannot show unit/fleet numbers)

--- AUTO-DEFENSE ACTIVATED ---
Queued: 35x Phalanx
Training completes in: 41M 17S
Attack arrives in: 1H 30M (48M 43S buffer)
Resources spent: 1995 (wood: 945, sulfur: 1050)
```

### Failure Case - Not Enough Time
```
-- PIRATE ATTACK --
Plundering raid
from the pirate fortress Doom Island of Dread Pirate Roberts
to Sparta
arrival in: 8M

--- AUTO-TRAIN FAILED ---
Attack too close (8 min < 15 min safety buffer)
Consider reducing safety buffer in settings if needed.
```

### Failure Case - No Barracks
```
-- PIRATE ATTACK --
Plundering raid
from the pirate fortress Skull Cove of Captain Hook
to New Colony
arrival in: 2H 15M

--- AUTO-TRAIN FAILED ---
Target city has no barracks - cannot train defense
Build a barracks to enable auto-defense.
```

### Failure Case - Insufficient Resources
```
-- PIRATE ATTACK --
Plundering raid
from the pirate fortress Terror Bay of Long John Silver
to Rhodes
arrival in: 45M

--- AUTO-DEFENSE ACTIVATED ---
Queued: 8x Phalanx (wanted 25, insufficient resources)
Training completes in: 9M 26S
Attack arrives in: 45M (35M 34S buffer)
Resources spent: 456 (wood: 216, sulfur: 240)

⚠️ Only partial defense trained due to lack of resources
```

---

## Testing Plan

### Test Case 1: Normal Success Case
**Setup:**
- Enable auto-train, max 5000 resources, 10 min buffer
- City has barracks with sufficient resources
- Trigger pirate attack arriving in 2 hours

**Expected:**
- Units calculated and queued
- Training completes before attack (with buffer)
- Alert shows success message with details
- Resources deducted from city

**Verify:**
- Check barracks training queue
- Verify resource decrease
- Confirm units ready before attack

---

### Test Case 2: Time Constraint - Close Call
**Setup:**
- Attack arrives in 30 minutes
- Safety buffer: 10 minutes
- Available training time: 20 minutes

**Expected:**
- System calculates units that fit 20 min window
- Smaller quantity trained
- Success message shows tight timing

---

### Test Case 3: Time Constraint - Too Close
**Setup:**
- Attack arrives in 8 minutes
- Safety buffer: 10 minutes

**Expected:**
- NO training queued (attack too close)
- Failure message explains why
- No resources spent

---

### Test Case 4: Existing Training Queue
**Setup:**
- Barracks already training units (30 min remaining)
- Attack arrives in 1 hour
- Available time: 60 - 30 = 30 minutes

**Expected:**
- System accounts for existing queue
- Only queue units that fit remaining time
- Training completes before attack

---

### Test Case 5: No Barracks
**Setup:**
- Target city has no barracks built
- Attack detected

**Expected:**
- Graceful failure
- Clear error message
- No crash

---

### Test Case 6: Insufficient Resources
**Setup:**
- Max spend: 5000 resources
- City has only 500 resources available

**Expected:**
- Train what's affordable
- Success message with warning
- Partial defense better than none

---

### Test Case 7: Spending Limit Enforcement
**Setup:**
- Max spend: 2000 resources
- Could train 50 units (3000 resources)
- Has 4000 resources available

**Expected:**
- Only train ~33 units (within 2000 limit)
- Success message shows limit respected
- Resources spent ≤ 2000

---

### Test Case 8: Multiple Attacks
**Setup:**
- 2 pirate attacks on different cities simultaneously

**Expected:**
- Each city trains independently
- Both succeed (if resources available)
- 2 separate alert messages

---

### Test Case 9: Feature Disabled
**Setup:**
- Auto-train disabled in config
- Pirate attack detected

**Expected:**
- Normal alert message (no auto-train section)
- No training queued
- System works as before

---

### Test Case 10: Preferred Units
**Setup:**
- User configured: preferred_units = ["swordsman"]
- Barracks has phalanx + swordsman available

**Expected:**
- Prioritize swordsman over phalanx
- Train swordsman if time/resources allow
- Fallback to phalanx only if swordsman doesn't fit

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Time calculation error | Low | **CRITICAL** | Thorough testing, safety buffer, reuse existing code |
| Resource over-spending | Low | Medium | Hard limit enforcement, alert confirmation |
| Training won't complete | Low | High | Conservative calculations, buffer time |
| No barracks available | Medium | Low | Graceful failure, clear error message |
| Fork merge conflicts | Low | Low | Minimal changes to existing files |
| Feature breaks alerts | Low | **CRITICAL** | Try-catch wrapper, separate module |
| User confusion | Medium | Low | Clear setup prompts, detailed alerts |

**Overall Risk**: **LOW-MEDIUM**

**Critical mitigations:**
- Safety buffer prevents close calls
- Try-catch prevents breaking alert system
- All calculations conservative (round down)

---

## Dependencies

### Required Before Implementation:
- ✅ Pirate detection working (from base branch)
- ✅ `trainArmy.py` functions available (for reuse)
- ✅ Session data storage working (for config)
- ✅ Alert system working (for notifications)

### Blocks:
- Nothing (self-contained feature)

---

## Out of Scope (Future Enhancements)

### Enhancement 1: Cross-City Defense
**Idea**: Train in multiple cities, send reinforcements to target

**Why later**: Complex (requires ship movement, timing coordination)

---

### Enhancement 2: Smart Unit Selection
**Idea**: Use AI to select optimal unit mix (rock-paper-scissors)

**Why later**: Game balance research needed, current approach sufficient

---

### Enhancement 3: Global Spending Limit
**Idea**: Max resources per DAY across all attacks

**Why later**: Requires persistent state tracking, edge case

---

### Enhancement 4: Predictive Training
**Idea**: Pre-train units based on attack patterns/history

**Why later**: Requires data collection, ML model, significant complexity

---

## Success Criteria

### Must Have (MVP):
1. ✅ Auto-train triggers on pirate attack detection
2. ✅ Units complete training BEFORE attack arrives
3. ✅ Respects user spending limit
4. ✅ Graceful failure (no crashes)
5. ✅ Clear alert messages (success/failure)

### Should Have:
6. ✅ Safety buffer prevents too-close attacks
7. ✅ Accounts for existing training queue
8. ✅ Works with any unit type available
9. ✅ Minimal changes to existing files (fork-friendly)

### Nice to Have:
10. ⏳ Preferred unit type configuration
11. ⏳ Partial training alerts (insufficient resources)
12. ⏳ Statistics tracking (resources spent over time)

---

## Implementation Estimate

### Time Breakdown:
- **Phase 1** (Core module): 6-8 hours
  - Time calculations: 2 hours
  - Unit selection logic: 2 hours
  - Resource management: 1 hour
  - Queue execution: 1 hour
  - Error handling: 1-2 hours

- **Phase 2** (Integration): 2-3 hours
  - Modify `alertAttacks.py`: 1 hour
  - Testing integration: 1-2 hours

- **Phase 3** (Configuration): 2 hours
  - Setup prompts: 1 hour
  - Session data: 1 hour

- **Testing**: 4-6 hours
  - Unit tests: 2 hours
  - Integration tests: 2-4 hours

**Total**: 14-19 hours

---

## Next Steps

### Immediate (This Session):
1. ✅ Create feature branch (DONE)
2. ✅ Write kick-off analysis (THIS DOCUMENT)
3. ⏳ Review with user (GET APPROVAL)

### After Approval:
4. Implement `autoTrainDefense.py` (core logic)
5. Modify `alertAttacks.py` (integration)
6. Test thoroughly (all test cases)
7. Commit and push to branch
8. User testing / feedback
9. Refinements if needed
10. Merge when stable

---

## Questions for User

1. **Unit preferences**: Any specific units to prioritize? (e.g., always train phalanx first)

2. **Spending limit**: Is "resource value" (sum of all resources) the right metric, or should we use gold equivalent?

3. **Safety buffer**: Is 10 minutes default reasonable, or prefer more conservative (15-20 min)?

4. **Multiple attacks**: If 3 attacks in 1 hour, train for all 3 (up to limit each), or global limit?

5. **Alert verbosity**: Current examples detailed enough, or prefer more/less info?

6. **Feature scope**: Anything missing from this analysis that should be included?

---

**Created**: 2025-11-14
**Status**: Kick-off Analysis Complete - Awaiting User Approval
**Branch**: `claude/auto-train-defense-01B2FzQ1cMSE1xLwvcXrRM1b`
**Next**: User review → Implementation Phase 1

---

## Technical Notes

### Code Location Reference
- Base detection: `alertAttacks.py:302-349` (pirate classification)
- Training logic: `trainArmy.py:48-163` (reusable functions)
- Config pattern: `autoPirate.py:138-143` (session data storage)

### API Endpoints Used
- `view=militaryAdvisor` - attack detection (existing)
- `view=barracks` - unit data & training (existing)
- No new API calls needed ✓

### Data Flow
```
Pirate detected → Extract timing → Call autoTrainDefense() →
  → Get city data → Calculate time → Select units →
  → Check resources → Queue training → Return result →
→ Append to alert → Send to Telegram
```

**Clean, linear flow - no complex state management needed.**
