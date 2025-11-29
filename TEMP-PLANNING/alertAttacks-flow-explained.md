# How alertAttacks Works: Complete Flow Explanation

**File**: `ikabot/function/alertAttacks.py`

---

## Overview

alertAttacks is a background monitoring service that:
1. Polls Ikariam military advisor every N minutes
2. Detects incoming hostile movements (attacks)
3. Sends Telegram alerts when new attacks appear
4. Allows user to activate vacation mode via Telegram response

---

## Complete Flow (Start to Finish)

### Stage 1: User Starts the Feature

**Triggered from**: CLI menu option (usually option 5 or similar)

```python
# From command_line.py - user selects alertAttacks
menu_actions[5] = alertAttacks  # Example
```

**What happens**:

```python
def alertAttacks(session, event, stdin_fd, predetermined_input):
    # Line 25-26: Setup stdin for CLI input
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input

    # Line 28-30: Check if Telegram is configured
    if checkTelegramData(session) is False:
        event.set()
        return  # Exit if no Telegram configured

    # Line 32-39: Ask user: How often to check for attacks?
    banner()
    minutes = read(
        msg="How often should I search for attacks?(min:3, default: 20): ",
        min=3,
        default=20
    )
    print("I will check for attacks every {:d} minutes".format(minutes))
    enter()
```

**User interaction**:
```
How often should I search for attacks?(min:3, default: 20): 20
I will check for attacks every 20 minutes
Press enter to continue...
```

### Stage 2: Background Process Spawn

```python
    # Line 47-48: Detach from parent process
    set_child_mode(session)
    event.set()  # Signal parent that setup is complete

    # Line 50-51: Set status info
    info = "\nI check for attacks every {:d} minutes\n".format(minutes)
    setInfoSignal(session, info)

    # Line 52-58: Start main loop with error handling
    try:
        do_it(session, minutes)  # Main monitoring loop
    except Exception as e:
        msg = "Error in:\n{}\nCause:\n{}".format(info, traceback.format_exc())
        sendToBot(session, msg)  # Send error to Telegram
    finally:
        session.logout()
```

**Process status** (visible in CLI table):
```
PID     Action        Status
13407   alertAttacks  I check for attacks every 20 minutes
```

### Stage 3: Response Thread Started

**Location**: `do_it()` function, line 102-104

```python
def do_it(session, minutes):
    # Start background thread to listen for Telegram responses
    thread = threading.Thread(target=respondToAttack, args=(session,))
    thread.start()
```

**What this thread does** (runs forever in parallel):

```python
def respondToAttack(session):
    while True:
        time.sleep(60 * 3)  # Check every 3 minutes

        # Get messages from Telegram
        responses = getUserResponse(session)

        for response in responses:
            # Parse: "<pid>:<action>"  e.g., "13407:1"
            rta = re.search(r"(\d+):?\s*(\d+)", response)

            if rta and int(rta.group(1)) == os.getpid():
                action = int(rta.group(2))

                if action == 1:
                    # User requested vacation mode
                    activateVacationMode(session)
                else:
                    sendToBot(session, "Invalid command: {:d}".format(action))
```

**Purpose**: Allows user to respond to alerts via Telegram (e.g., activate vacation mode)

### Stage 4: Main Monitoring Loop

**Location**: `do_it()` function, line 106-165

```python
    knownAttacks = []  # Track which attacks we've already alerted

    while True:  # Loop forever
        currentAttacks = []  # Current cycle's attacks

        try:
            # --- STEP 1: Fetch HTML page ---
            html = session.get()  # GET request to current page
            city_id = re.search(r"currentCityId:\s(\d+),", html).group(1)

            # --- STEP 2: Post to military advisor API ---
            url = "view=militaryAdvisor&..."
            movements_response = session.post(url)

            # --- STEP 3: Parse JSON response ---
            postdata = json.loads(movements_response, strict=False)
            militaryMovements = postdata[1][1][2]["viewScriptParams"][
                "militaryAndFleetMovements"
            ]
            timeNow = int(postdata[0][1]["time"])

            # --- STEP 4: Filter for hostile movements ---
            for militaryMovement in [
                mov for mov in militaryMovements if mov["isHostile"]
            ]:
                event_id = militaryMovement["event"]["id"]
                currentAttacks.append(event_id)

                # --- STEP 5: Check if this is a NEW attack ---
                if event_id not in knownAttacks:
                    knownAttacks.append(event_id)

                    # --- STEP 6: Extract attack data ---
                    missionText = militaryMovement["event"]["missionText"]
                    origin = militaryMovement["origin"]
                    target = militaryMovement["target"]
                    amountTroops = militaryMovement["army"]["amount"]
                    amountFleets = militaryMovement["fleet"]["amount"]
                    timeLeft = int(militaryMovement["eventTime"]) - timeNow

                    # --- STEP 7: Build and send alert ---
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

                    sendToBot(session, msg)  # SEND TO TELEGRAM

        except Exception as e:
            # Error handling - send to Telegram
            msg = "Error in:\n{}\nCause:\n{}".format(info, traceback.format_exc())
            sendToBot(session, msg)

        # --- STEP 8: Clean up old attacks ---
        for event_id in list(knownAttacks):
            if event_id not in currentAttacks:
                knownAttacks.remove(event_id)  # Attack no longer exists (landed or cancelled)

        # --- STEP 9: Sleep until next check ---
        time.sleep(minutes * 60)  # Sleep N minutes
```

---

## Detailed Breakdown of Key Steps

### Step 1: Fetch HTML Page

```python
html = session.get()
city_id = re.search(r"currentCityId:\s(\d+),", html).group(1)
```

**Why**: Need current city ID to construct API URL

**What it gets**: Full HTML of current Ikariam page

**Example**: `currentCityId: 54321,` → extracts `54321`

### Step 2: Post to Military Advisor API

```python
url = "view=militaryAdvisor&oldView=city&oldBackgroundView=city&backgroundView=city&currentCityId={}&actionRequest={}&ajax=1"
movements_response = session.post(url)
```

**What this does**: Requests military advisor data via AJAX

**API endpoint**: `/index.php` (POST with view=militaryAdvisor)

**Returns**: JSON with all military/fleet movements

### Step 3: Parse API Response

```python
postdata = json.loads(movements_response, strict=False)
militaryMovements = postdata[1][1][2]["viewScriptParams"]["militaryAndFleetMovements"]
timeNow = int(postdata[0][1]["time"])
```

**Structure** (nested arrays/objects):
```
postdata = [
    [                           # Index 0
        {...},
        {"time": 1699876543}    # Server time
    ],
    [                           # Index 1
        {...},
        [                       # Index [1][1]
            {...},
            {...},
            {                   # Index [1][1][2]
                "viewScriptParams": {
                    "militaryAndFleetMovements": [
                        {...movement1...},
                        {...movement2...},
                        {...movement3...}
                    ]
                }
            }
        ]
    ]
]
```

**What we extract**:
- `militaryMovements`: Array of all movements
- `timeNow`: Server timestamp (for calculating arrival times)

### Step 4: Filter for Hostile Movements

```python
for militaryMovement in [
    mov for mov in militaryMovements if mov["isHostile"]
]:
```

**List comprehension breakdown**:
1. Take all movements in `militaryMovements`
2. Keep only those where `mov["isHostile"] == true`
3. Loop through filtered list

**What gets filtered OUT**:
- Your own transports (isHostile=false, isOwnArmyOrFleet=true)
- Friendly movements (isHostile=false)
- Trade ships (isHostile=false)

**What gets filtered IN**:
- Incoming attacks (isHostile=true, isOwnArmyOrFleet=false)
- **YOUR pirate missions** (isHostile=true, isOwnArmyOrFleet=true) ← THIS IS THE BUG!

### Step 5: Check if New Attack

```python
event_id = militaryMovement["event"]["id"]
currentAttacks.append(event_id)

if event_id not in knownAttacks:
    knownAttacks.append(event_id)
```

**Why**:
- Each movement has unique event ID
- Track IDs in `knownAttacks` list
- Only alert ONCE per attack (not every check interval)

**Example**:
```
First check:   event_id=12345 not in knownAttacks → ALERT + add to list
Second check:  event_id=12345 in knownAttacks → skip (already alerted)
Third check:   event_id=12345 in knownAttacks → skip
```

### Step 6: Extract Attack Data

```python
missionText = militaryMovement["event"]["missionText"]  # "Přepadení (probíhá)"
origin = militaryMovement["origin"]                     # {name, avatarName, ...}
target = militaryMovement["target"]                     # {name, ...}
amountTroops = militaryMovement["army"]["amount"]       # 0
amountFleets = militaryMovement["fleet"]["amount"]      # 0
timeLeft = int(militaryMovement["eventTime"]) - timeNow # Seconds until arrival
```

**Movement object structure**:
```javascript
{
  "isHostile": true,
  "isOwnArmyOrFleet": false,  // ← KEY: Distinguishes own vs incoming
  "event": {
    "id": 12345,
    "missionText": "Přepadení (probíhá)"
  },
  "origin": {
    "name": "Hr4fnsfj0rdur",
    "avatarName": "_K4_"
  },
  "target": {
    "name": "Řím"
  },
  "army": {
    "amount": 0
  },
  "fleet": {
    "amount": 0
  },
  "eventTime": 1699880143
}
```

### Step 7: Build Alert Message

```python
msg = "-- ALERT --\n"
msg += missionText + "\n"
msg += "from the city {} of {}\n".format(origin["name"], origin["avatarName"])
msg += "a {}\n".format(target["name"])
msg += "{} units\n".format(amountTroops)
msg += "{} fleet\n".format(amountFleets)
msg += "arrival in: {}\n".format(daysHoursMinutes(timeLeft))
msg += "If you want to put the account in vacation mode send:\n"
msg += "{:d}:1".format(os.getpid())

sendToBot(session, msg)
```

**Result** (sent to Telegram):
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

### Step 8: Clean Up Old Attacks

```python
for event_id in list(knownAttacks):
    if event_id not in currentAttacks:
        knownAttacks.remove(event_id)
```

**Why**: Attacks that landed or were cancelled no longer appear in API response

**Example**:
```
knownAttacks = [12345, 12346, 12347]
currentAttacks = [12345, 12346]        # 12347 landed
→ Remove 12347 from knownAttacks
knownAttacks = [12345, 12346]
```

### Step 9: Sleep

```python
time.sleep(minutes * 60)
```

Wait N minutes (e.g., 20 minutes = 1200 seconds) then repeat loop.

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────┐
│  User starts alertAttacks from CLI menu     │
│  → Asks: How often to check? (20 min)      │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│  Background process spawned                 │
│  → set_child_mode()                         │
│  → event.set() (returns to menu)            │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│  Start response thread (respondToAttack)    │
│  → Polls Telegram every 3 min for commands │
└─────────────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│  MAIN LOOP (every N minutes):               │
│                                             │
│  1. GET HTML page                           │
│     → Extract current city ID               │
│                                             │
│  2. POST to militaryAdvisor API             │
│     → Get JSON response (postdata)          │
│                                             │
│  3. Extract militaryMovements array         │
│     → postdata[1][1][2]["viewScriptParams"] │
│                                             │
│  4. Filter: Keep only isHostile==true       │
│     → [mov for mov in all if mov["isHostile"]]
│                                             │
│  5. For each hostile movement:              │
│     → Check if event_id is new              │
│     → If new: Extract data & send alert     │
│     → If known: Skip                        │
│                                             │
│  6. Clean up landed attacks                 │
│     → Remove from knownAttacks              │
│                                             │
│  7. Sleep N minutes                         │
│     → Repeat                                │
└─────────────────┬───────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────┐
│  Alert sent to Telegram                     │
│  → User sees attack notification            │
│  → Can respond: "13407:1" for vacation mode │
└─────────────────────────────────────────────┘
```

---

## Current Problems

### Problem 1: No Attack Type Detection

**Line 124-126**: Only checks `isHostile`
```python
for militaryMovement in [
    mov for mov in militaryMovements if mov["isHostile"]
]:
```

**Missing**: No check for:
- Pirate vs player
- Own movements vs incoming
- Attack type (raid/pillage/occupy)

### Problem 2: Generic Alert for Everything

**Line 142**: Always says "-- ALERT --"
```python
msg = "-- ALERT --\n"
```

**Result**: Can't distinguish:
- Pirate attacks (minor, common)
- Player attacks (serious, rare)
- Different attack types

### Problem 3: No Logging/Debugging

**No debug output**: Can't see what data is available

**No logs**: Can't analyze after the fact

---

## What We Don't Know

From current code, we DON'T know:
1. What other fields exist in `militaryMovement` object?
2. Is there `missionType`, `avatarId`, `isPiracyRaid`, etc.?
3. How does game distinguish pirates from players?
4. What other movement types exist?

**This is why we need debug logging!**

---

## Summary

**Current Flow**:
1. User starts → asks interval
2. Background process → loops forever
3. Every N minutes:
   - Fetch military movements via API
   - Filter for `isHostile == true`
   - Alert if new attack
   - Sleep
4. Response thread → listens for Telegram commands

**Current Detection**:
- ✅ Detects attacks (works)
- ❌ No type distinction (doesn't work)
- ❌ No pirate detection (doesn't work)
- ❌ No debug logging (can't fix without data)

**Fix Strategy**:
1. Add debug logging (feat-09)
2. Collect attack samples
3. Analyze API structure
4. Implement proper detection
5. Test with real attacks
