# Issue #04: Alert System Doesn't Distinguish Pirate Attacks from Player Attacks

**Status**: Analysis Complete
**Priority**: MEDIUM
**Severity**: Medium (causes confusion, not critical)
**Component**: alertAttacks.py
**Type**: Enhancement - Missing Feature

---

## Problem Report

User received alert for incoming pirate attack:
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

**Issue**: Alert says "-- ALERT --" for everything, doesn't distinguish:
- ❌ Player attacks (serious - major threat, need full defense)
- ❌ Pirate attacks (minor - small raids, less dangerous)

**Evidence this is a pirate attack:**
- City: "Hr4fnsfj0rdur" (typical pirate fortress name)
- Player: "_K4_" (pirate identifier, not real player)
- Units: 0/0 (pirates hide their forces in game)

**User confusion**: "Is this a real player attacking me or just pirates?"

---

## Root Cause Analysis

### Current Code (alertAttacks.py:141-153)

```python
# send alert
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
```

**Problem**: Line 142 always says "-- ALERT --" regardless of attacker type.

**Missing logic**: No check to see if attacker is pirate vs player.

---

## How to Detect Pirates

### Method 1: Check avatarId (Most Reliable)

```python
origin = militaryMovement["origin"]
is_pirate = origin.get("avatarId", 1) == 0
```

Pirates are NPCs with `avatarId: 0` (or sometimes negative).

### Method 2: Check origin type

```python
is_pirate = origin.get("type") == "pirateFortress"
```

### Method 3: Check avatar name pattern

```python
# Pirates have special naming like "_K4_", "_B3_", etc.
is_pirate = origin["avatarName"].startswith("_") and origin["avatarName"].endswith("_")
```

**Recommended**: Use Method 1 (avatarId) as primary, Method 2 as fallback.

---

## Impact

### Current Behavior (Confusing)
```
-- ALERT --                    <- Same for everything
Přepadení (probíhá)
from the city Hr4fnsfj0rdur of _K4_
```

**User thinks**: "Oh no, a player is attacking! Need to prepare defenses!"
**Reality**: Just a minor pirate raid.

### Expected Behavior (Clear)
```
-- PIRATE ATTACK --            <- Clear label
Přepadení (probíhá)
from pirate fortress Hr4fnsfj0rdur of _K4_
```

**User knows**: "Just pirates, not urgent."

---

## Why This Matters

### Player Attacks
- **Serious threat**: Can steal resources, destroy buildings
- **Need preparation**: Build defenses, recall troops, hide resources
- **Rare**: Other players attacking is uncommon
- **Urgent**: Need immediate action

### Pirate Attacks
- **Minor threat**: Usually small raids
- **Less preparation**: Often ignorable or easy to defend
- **Common**: Pirates attack regularly as game mechanic
- **Less urgent**: Can often be ignored

**Alert should reflect severity!**

---

## Proposed Fix

### Minimal Enhancement

Add pirate detection before sending alert:

```python
# get information about the attack
missionText = militaryMovement["event"]["missionText"]
origin = militaryMovement["origin"]
target = militaryMovement["target"]
amountTroops = militaryMovement["army"]["amount"]
amountFleets = militaryMovement["fleet"]["amount"]
timeLeft = int(militaryMovement["eventTime"]) - timeNow

# Detect if attacker is pirate
is_pirate = (
    origin.get("avatarId", 1) == 0 or
    origin.get("type") == "pirateFortress"
)

# send alert with appropriate label
if is_pirate:
    msg = "-- PIRATE ATTACK --\n"
else:
    msg = "-- ALERT --\n"

msg += missionText + "\n"
msg += "from the {} {} of {}\n".format(
    "pirate fortress" if is_pirate else "city",
    origin["name"],
    origin["avatarName"]
)
msg += "to {}\n".format(target["name"])
msg += "{} units\n".format(amountTroops)
msg += "{} fleet\n".format(amountFleets)
msg += "arrival in: {}\n".format(daysHoursMinutes(timeLeft))
msg += "If you want to put the account in vacation mode send:\n"
msg += "{:d}:1".format(os.getpid())
sendToBot(session, msg)
```

### Enhanced Version (Optional Features)

```python
# Detect pirate
is_pirate = (
    origin.get("avatarId", 1) == 0 or
    origin.get("type") == "pirateFortress"
)

# Different alert based on type
if is_pirate:
    msg = "-- PIRATE ATTACK --\n"
    msg += "⚔️ " + missionText + "\n"
    msg += "from pirate fortress {} of {}\n".format(
        origin["name"], origin["avatarName"]
    )
    # Maybe skip vacation mode option for pirates
    # (user probably doesn't want vacation for minor pirate)
else:
    msg = "-- ⚠️ PLAYER ATTACK ⚠️ --\n"
    msg += "🚨 " + missionText + "\n"
    msg += "from the city {} of {}\n".format(
        origin["name"], origin["avatarName"]
    )
    # Keep vacation mode option for player attacks
    msg += "If you want to put the account in vacation mode send:\n"
    msg += "{:d}:1".format(os.getpid())

# Common info for both
msg += "to {}\n".format(target["name"])
msg += "{} units\n".format(amountTroops)
msg += "{} fleet\n".format(amountFleets)
msg += "arrival in: {}\n".format(daysHoursMinutes(timeLeft))

sendToBot(session, msg)
```

---

## Testing Plan

### Test Case 1: Pirate Attack (Your Bug Report)
1. Get attacked by pirate fortress
2. **Current**: Shows "-- ALERT --"
3. **Expected**: Shows "-- PIRATE ATTACK --"

### Test Case 2: Player Attack
1. Get attacked by real player
2. **Current**: Shows "-- ALERT --"
3. **Expected**: Shows "-- ALERT --" or "-- PLAYER ATTACK --"

### Test Case 3: Multiple Simultaneous
1. Pirates attack + player attacks
2. **Expected**: Different labels for each

---

## Priority Justification

**MEDIUM Priority** because:
1. ✅ **User confusion**: Can't tell pirate from player attacks
2. ✅ **Common**: Pirates attack frequently
3. ✅ **Easy fix**: ~10 lines, low risk
4. ❌ **Not breaking**: Alert still works, just lacks detail

**Not HIGH** because:
- System works (detects attacks correctly)
- User can figure it out by reading city/player names
- Not causing failures or data loss

---

## Example Output

### Before (Current)
```
-- ALERT --
Přepadení (probíhá)
from the city Hr4fnsfj0rdur of _K4_
a Řím
0 units
0 fleet
arrival in: 4M
If you want to put the account in vacation mode send:
13407:1
```

### After (Fixed)
```
-- PIRATE ATTACK --
Přepadení (probíhá)
from pirate fortress Hr4fnsfj0rdur of _K4_
to Řím
0 units
0 fleet
arrival in: 4M
```

### Player Attack (Enhanced)
```
-- ⚠️ PLAYER ATTACK ⚠️ --
🚨 Occupation (in progress)
from the city Athens of RealPlayer123
to Řím
250 units
50 fleet
arrival in: 1H 23M
If you want to put the account in vacation mode send:
13407:1
```

---

## Code Review Findings

### Related Code to Check

1. **shipMovements.py**: Also displays military movements
   - Check if it has same issue
   - Line 96: Uses `movement["event"]["missionText"]`
   - Might need same enhancement

2. **Pattern in codebase**:
   ```bash
   grep -r "avatarId" ikabot/
   ```
   - See if other code distinguishes pirates
   - Learn from existing patterns

---

## Recommended Commit Message

```
Distinguish pirate attacks from player attacks in alerts

Issue: alertAttacks.py shows "-- ALERT --" for all incoming
attacks, making pirates and players indistinguishable.

Impact: User confusion - can't tell if it's serious player
attack or minor pirate raid.

Fix: Detect pirate attackers by checking:
- origin["avatarId"] == 0 (pirates are NPCs)
- origin["type"] == "pirateFortress" (fallback)

Changes:
- alertAttacks.py:141 - Add pirate detection
- alertAttacks.py:142 - Label as "PIRATE ATTACK" vs "ALERT"
- alertAttacks.py:144 - Change "city" to "pirate fortress" for pirates

Result: Clear distinction between attack types.

Example output:
  Before: "-- ALERT -- from the city Hr4fnsfj0rdur of _K4_"
  After:  "-- PIRATE ATTACK -- from pirate fortress Hr4fnsfj0rdur of _K4_"
```

---

## Implementation Notes

### Minimal Changes
- ~10 lines added
- No breaking changes
- Backward compatible
- Same alert for player attacks

### Testing Requirements
- Test with pirate attack
- Test with player attack
- Test with both simultaneous
- Verify vacation mode still works for players

### Optional Enhancements (Future)
- Different emoji/formatting for pirates vs players
- Skip vacation mode option for pirates
- Add pirate raid statistics
- Configurable: alert for pirates yes/no

---

**Created**: 2025-11-12
**Status**: Ready for Implementation
**Estimated Effort**: 15 minutes
**Risk**: LOW (addition only, no logic changes)
