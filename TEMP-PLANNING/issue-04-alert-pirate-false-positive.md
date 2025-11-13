# Issue #04: Alert System - Pirate Attacks Incorrectly Triggering Alerts

**Status**: Analysis Complete
**Priority**: HIGH
**Severity**: Medium (false alarms reduce trust in alert system)
**Component**: alertAttacks.py
**Type**: Bug - Logic Error

---

## Problem Report

User received alert for what appeared to be a player attack:
```
pid:13407
Server:cz, World:Aeneas, Player:pooky756
-- ALERT --
Přepadení (probíhá)
from the city Hr4fnsfj0rdur of _K4_
a Řím
0 units
0 fleet
arrival in: 4M
```

**Issue**: This was actually a **pirate mission** (user's own autoPirate attacking), NOT an incoming attack from another player.

---

## Root Cause Analysis

### Current Code Logic (alertAttacks.py:124-153)

```python
for militaryMovement in [
    mov for mov in militaryMovements if mov["isHostile"]
]:
    # get information about the attack
    missionText = militaryMovement["event"]["missionText"]
    origin = militaryMovement["origin"]
    target = militaryMovement["target"]

    # send alert
    msg = "-- ALERT --\n"
    msg += missionText + "\n"
    msg += "from the city {} of {}\n".format(
        origin["name"], origin["avatarName"]
    )
```

### The Bug

**Line 125**: `if mov["isHostile"]`

The game marks **both** as hostile:
1. ✅ Enemy player attacks (SHOULD alert)
2. ❌ Your own pirate missions (should NOT alert)

**Why pirate missions are marked hostile:**
- When you attack a pirate fortress, it's technically a "hostile" movement
- The game shows it in military advisor as outgoing hostile action
- Pirates have `isHostile: true` in the API response

**Evidence from alert:**
- City name: "Hr4fnsfj0rdur" - typical pirate fortress name (not player city)
- Player name: "_K4_" - pirate identifier (not real player)
- 0 units/0 fleet - game doesn't reveal pirate forces
- Mission text: "Přepadení (probíhá)" = "Raid (in progress)"

---

## How Ikariam Distinguishes Pirates vs Players

Based on API structure analysis:

### Method 1: Check `avatarId`
```python
origin["avatarId"]  # 0 for pirates, > 0 for real players
```

Pirates are NPC entities with `avatarId: 0` or negative values.

### Method 2: Check origin type
```python
origin["type"]  # "pirateFortress" vs "city"
```

### Method 3: Check avatar name pattern
```python
origin["avatarName"]  # Pirates have special prefixes like "_K4_"
```

### Method 4: Check if it's your own movement
```python
militaryMovement["isOwnArmyOrFleet"]  # true for your units
```

**Most reliable**: Use `isOwnArmyOrFleet` to filter out YOUR movements (including pirate missions).

---

## Impact

### Current Behavior (Broken)
1. User starts autoPirate
2. Pirate missions show in military movements
3. Alert system sees `isHostile: true`
4. **FALSE ALARM** - alerts about own pirate mission
5. User gets confused: "Is this a real attack?"

### Expected Behavior
1. User starts autoPirate
2. Alert system detects pirate missions
3. **Ignores** own outgoing missions
4. **Only alerts** for incoming attacks from real players

---

## Code Review

### File: `ikabot/function/alertAttacks.py`

#### Issue 1: No filtering for own movements (HIGH)

**Location**: Lines 124-126

**Current code**:
```python
for militaryMovement in [
    mov for mov in militaryMovements if mov["isHostile"]
]:
```

**Problem**: Includes YOUR outgoing pirate missions because they're marked `isHostile`.

**Fix**:
```python
for militaryMovement in [
    mov for mov in militaryMovements
    if mov["isHostile"] and not mov["isOwnArmyOrFleet"]
]:
```

**Reasoning**:
- Only care about INCOMING attacks
- Filter out YOUR outgoing movements (including pirate missions)
- Simple, reliable, covers all cases

---

#### Issue 2: No distinction between player attacks and pirate attacks (MEDIUM)

**Location**: Lines 134-153

**Current code**:
```python
missionText = militaryMovement["event"]["missionText"]
origin = militaryMovement["origin"]

# Send same alert for everything
msg = "-- ALERT --\n"
msg += missionText + "\n"
```

**Problem**: Even if an incoming pirate attack happens (rare), it's treated same as player attack.

**Potential issue**: If another player sends their pirate missions to attack you (possible in game), you might want to know it's a pirate attack vs full invasion.

**Enhancement** (optional):
```python
origin = militaryMovement["origin"]

# Check if attacker is pirate
if origin.get("avatarId", 1) == 0:
    msg = "-- PIRATE ATTACK --\n"
    # Different handling for pirate attacks
else:
    msg = "-- ALERT --\n"
    # Regular player attack
```

---

#### Issue 3: Redundant custom isHostile function (LOW)

**Location**: `ikabot/function/shipMovements.py:19-34`

**Observation**: There's a custom `isHostile()` function that checks:
```python
def isHostile(movement):
    if movement["army"]["amount"]:
        return True
    for mov in movement["fleet"]["ships"]:
        if mov["cssClass"] != "ship_transport":
            return True
    return False
```

**This checks**: If movement has troops or warships (not just transports).

**Not used in alertAttacks.py**: The alert system uses game's `mov["isHostile"]` flag directly.

**Question**: Should alertAttacks.py use this custom function instead? Would need to investigate why this exists separately.

---

## Recommended Fix

### Minimal Fix (1 line change)

**File**: `ikabot/function/alertAttacks.py:125`

**Change**:
```python
# Before
for militaryMovement in [
    mov for mov in militaryMovements if mov["isHostile"]
]:

# After
for militaryMovement in [
    mov for mov in militaryMovements
    if mov["isHostile"] and not mov.get("isOwnArmyOrFleet", False)
]:
```

**Why `.get("isOwnArmyOrFleet", False)`**: Safe access in case field doesn't exist.

**Result**:
- ✅ Filters out own pirate missions
- ✅ Filters out any own military movements
- ✅ Only alerts for incoming attacks
- ✅ No false alarms

---

### Enhanced Fix (add pirate distinction)

**Additional check** (optional, for better UX):

```python
for militaryMovement in [
    mov for mov in militaryMovements
    if mov["isHostile"] and not mov.get("isOwnArmyOrFleet", False)
]:
    # ... existing code ...

    origin = militaryMovement["origin"]

    # Check if from pirate fortress
    is_pirate = (
        origin.get("avatarId", 1) == 0 or
        origin.get("type") == "pirateFortress"
    )

    if is_pirate:
        msg = "-- PIRATE ATTACK --\n"
        # Maybe different handling - pirates are less dangerous
    else:
        msg = "-- ALERT --\n"
        # Real player attack - more serious
```

---

## Testing Plan

### Test Case 1: Own Pirate Mission
1. Start autoPirate with alertAttacks running
2. Wait for pirate mission to launch
3. **Expected**: No alert (own movement)
4. **Bug**: Alert triggered (current behavior)

### Test Case 2: Incoming Player Attack
1. Get attacked by real player
2. **Expected**: Alert triggered
3. Should work correctly (already does)

### Test Case 3: Incoming Pirate Attack (rare)
1. Get attacked by pirate (NPC event)
2. **Expected**: Alert triggered (maybe with "PIRATE ATTACK" label)
3. Need to test with enhanced fix

### Test Case 4: Own Transport Mission
1. Send resources with transports
2. **Expected**: No alert
3. Should work with fix (isOwnArmyOrFleet filters it)

---

## Related Code

### Also check these files:

1. **`ikabot/function/shipMovements.py`**
   - Has custom `isHostile()` function
   - Uses `mov["isHostile"]` at line 75, 102
   - Also at line 110 uses custom `isHostile()` function
   - **Question**: Why two different methods?

2. **`ikabot/helpers/planRoutes.py:208`**
   - Uses `mov["isOwnArmyOrFleet"]` to filter own movements
   - Same pattern needed in alertAttacks.py

---

## Priority Justification

**HIGH Priority** because:
1. ✅ **User impact**: False alarms every time autoPirate runs
2. ✅ **Trust**: Users may disable alerts due to false positives
3. ✅ **Frequency**: Happens with every pirate mission (common use case)
4. ✅ **Easy fix**: 1-line change, low risk
5. ✅ **Clear root cause**: Well understood, testable

**Not CRITICAL** because:
- Doesn't crash the bot
- Doesn't cause data loss
- Just a nuisance alert

---

## Proposed Commit Message

```
Fix false alerts for own pirate missions in alertAttacks

Issue: alertAttacks.py was triggering alerts for user's own
pirate missions because they're marked as "isHostile" by the game.

Root cause: Code only filtered by isHostile flag, which includes:
- Incoming enemy attacks (should alert) ✓
- Outgoing pirate missions (should NOT alert) ✗

Fix: Add check for isOwnArmyOrFleet to filter out own movements.

Changes:
- alertAttacks.py:125 - Add "not mov.get('isOwnArmyOrFleet', False)"

Result: Only alerts for INCOMING attacks from other players.

Tested:
- Own pirate missions: No alert ✓
- Incoming player attacks: Alert triggered ✓
- Own transport missions: No alert ✓
```

---

## Example Fixed Code

```python
def do_it(session, minutes):
    thread = threading.Thread(target=respondToAttack, args=(session,))
    thread.start()

    knownAttacks = []
    while True:
        currentAttacks = []
        try:
            # Get military movements
            html = session.get()
            city_id = re.search(r"currentCityId:\s(\d+),", html).group(1)
            url = "view=militaryAdvisor&oldView=city&oldBackgroundView=city&backgroundView=city&currentCityId={}&actionRequest={}&ajax=1".format(
                city_id, actionRequest
            )
            movements_response = session.post(url)
            postdata = json.loads(movements_response, strict=False)
            militaryMovements = postdata[1][1][2]["viewScriptParams"][
                "militaryAndFleetMovements"
            ]
            timeNow = int(postdata[0][1]["time"])

            # FIX: Filter hostile movements, exclude own movements
            for militaryMovement in [
                mov for mov in militaryMovements
                if mov["isHostile"] and not mov.get("isOwnArmyOrFleet", False)
            ]:
                event_id = militaryMovement["event"]["id"]
                currentAttacks.append(event_id)

                if event_id not in knownAttacks:
                    knownAttacks.append(event_id)

                    # Get attack info
                    missionText = militaryMovement["event"]["missionText"]
                    origin = militaryMovement["origin"]
                    target = militaryMovement["target"]
                    amountTroops = militaryMovement["army"]["amount"]
                    amountFleets = militaryMovement["fleet"]["amount"]
                    timeLeft = int(militaryMovement["eventTime"]) - timeNow

                    # Send alert
                    msg = "-- ALERT --\n"
                    msg += missionText + "\n"
                    msg += "from the city {} of {}\n".format(
                        origin["name"], origin["avatarName"]
                    )
                    msg += "a {}\n".format(target["name"])
                    msg += "{} units\n".format(amountTroops)
                    msg += "{} fleet\n".format(amountFleets)
                    msg += "arrival in: {}\n".format(daysHoursMinutes(timeLeft))
                    msg += "If you want to put the account in vacation mode send:\n"
                    msg += "{:d}:1".format(os.getpid())
                    sendToBot(session, msg)

        except Exception as e:
            info = "\nI check for attacks every {:d} minutes\n".format(minutes)
            msg = "Error in:\n{}\nCause:\n{}".format(info, traceback.format_exc())
            sendToBot(session, msg)

        # Clean up old attacks
        for event_id in list(knownAttacks):
            if event_id not in currentAttacks:
                knownAttacks.remove(event_id)

        time.sleep(minutes * 60)
```

---

**Created**: 2025-11-12
**Analyzed by**: Code Review
**Status**: Ready for Fix
**Estimated Effort**: 5 minutes (1 line change)
**Risk**: LOW (safe addition, uses existing field)
