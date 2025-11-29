# Feature #04: CLI Menu Map & User Flow Analysis

**Status**: Analysis Complete
**Priority**: HIGH (Foundation for Telegram Port)
**Component**: Command Line Interface (ikabot/command_line.py)
**Type**: Documentation & Analysis

---

## Purpose

This document maps all CLI menu paths, describes each feature's purpose, and analyzes user flows to identify:
1. What each menu option does and when to use it
2. Step-by-step user interaction flows
3. Missing back buttons and points of no return
4. Input patterns and validation requirements

This analysis is critical for porting to Telegram with minimal architecture changes.

---

## Main Menu Structure

**File**: `ikabot/command_line.py:154-177`

### Top-Level Menu Options

| Option | Label | Function | Submenu? |
|--------|-------|----------|----------|
| 0 | Exit | Exit program | No |
| 1 | Construction list | `constructionList()` | No |
| 2 | Send resources | `sendResources()` | No |
| 3 | Distribute resources | `distributeResources()` | No |
| 4 | Account status | `getStatus()` | No |
| 5 | Activate Shrine | `activateShrine()` | No |
| 6 | Login daily | `loginDaily()` | No |
| 7 | Alerts / Notifications | Submenu → 701, 702 | **Yes** |
| 8 | Marketplace | Submenu → 801, 802 | **Yes** |
| 9 | Donate | Submenu → 901, 902 | **Yes** |
| 10 | Activate vacation mode | `vacationMode()` | No |
| 11 | Activate miracle | `activateMiracle()` | No |
| 12 | Military actions | Submenu → 1201, 1202 | **Yes** |
| 13 | See movements | `shipMovements()` | No |
| 14 | Construct building | `constructBuilding()` | No |
| 15 | Update Ikabot | `update()` | No |
| 16 | Ikabot Web Server | `webServer()` | No |
| 17 | Auto-Pirate | `autoPirate()` | No |
| 18 | Investigate | `investigate()` | No |
| 19 | Attack / Grind barbarians | Submenu → 1901, 1902 | **Yes** |
| 20 | Dump / Monitor world | Submenu → 2001, 2002 | **Yes** |
| 21 | Options / Settings | Submenu → 2101-2108 | **Yes** |
| 22 | Consolidate resources | `consolidateResources()` | No |
| 23 | Set Production | `modifyProduction()` | No |

---

## Complete Menu Map with Descriptions

### Direct Actions (No Submenu)

#### (0) Exit
- **Function**: Exit the program
- **Purpose**: Clean shutdown (processes continue on Unix, die on Windows if terminal closed)
- **When to use**: Done using Ikabot for now
- **Process**: Direct exit, no confirmation

#### (1) Construction List
- **Function**: `constructionList()`
- **Purpose**: Automate building construction across cities
- **When to use**: Want to queue buildings automatically based on priorities
- **Good for**: Hands-off empire building, overnight construction automation

#### (2) Send Resources
- **Function**: `sendResources()`
- **Purpose**: Send resources from one city to another (own or foreign)
- **When to use**: Need to transport resources between cities
- **Good for**: Consolidating resources, trading with allies, supplying remote cities

#### (3) Distribute Resources
- **Function**: `distributeResources()`
- **Purpose**: Automatically distribute resources from source cities to destinations
- **When to use**: Want automated resource balancing across empire
- **Good for**: Keeping all cities supplied, resource equalization, continuous logistics

#### (4) Account Status
- **Function**: `getStatus()`
- **Purpose**: View account-wide statistics and individual city details
- **When to use**: Want overview of empire (resources, production, ships)
- **Good for**: Quick empire health check, production monitoring, planning

#### (5) Activate Shrine
- **Function**: `activateShrine()`
- **Purpose**: Activate island shrine bonuses
- **When to use**: Want to use shrine effects (requires resources)
- **Good for**: Temporary boosts to production/military/research

#### (6) Login Daily
- **Function**: `loginDaily()`
- **Purpose**: Automatically login daily to collect daily bonuses
- **When to use**: Want to ensure daily login rewards without manual play
- **Good for**: Passive players, collecting daily bonuses automatically

#### (10) Activate Vacation Mode
- **Function**: `vacationMode()`
- **Purpose**: Put account into vacation mode (protection from attacks)
- **When to use**: Going away for extended period, need protection
- **Good for**: Vacations, breaks from game, avoiding raids while inactive

#### (11) Activate Miracle
- **Function**: `activateMiracle()`
- **Purpose**: Activate wonder of the world miracles
- **When to use**: Have access to wonder and want to activate miracle
- **Good for**: Endgame wonder activation, alliance coordination

#### (13) See Movements
- **Function**: `shipMovements()`
- **Purpose**: View all ship movements (incoming and outgoing)
- **When to use**: Want to see fleet status and ETAs
- **Good for**: Monitoring trades, attacks, returns, coordinating fleets

#### (14) Construct Building
- **Function**: `constructBuilding()`
- **Purpose**: Build or upgrade a single building in a city
- **When to use**: Want to manually construct one specific building
- **Good for**: Quick single upgrades, manual building management

#### (15) Update Ikabot
- **Function**: `update()`
- **Purpose**: Check for and install Ikabot updates
- **When to use**: Want latest features and bug fixes
- **Good for**: Staying current with development

#### (16) Ikabot Web Server
- **Function**: `webServer()`
- **Purpose**: Start web interface for Ikabot (browser-based control)
- **When to use**: Prefer web UI over CLI, want remote access
- **Good for**: GUI users, mobile access, remote management

#### (18) Investigate
- **Function**: `investigate()`
- **Purpose**: Automatically investigate foreign cities (spy missions)
- **When to use**: Want intelligence on other players
- **Good for**: Military planning, scouting targets, gathering intel

#### (22) Consolidate Resources
- **Function**: `consolidateResources()`
- **Purpose**: Gather resources from multiple cities to one location
- **When to use**: Need to concentrate resources for big purchase/build
- **Good for**: Market operations, wonder building, major construction

#### (23) Set Production of Saw mill / Luxury good
- **Function**: `modifyProduction()`
- **Purpose**: Change what luxury good buildings produce
- **When to use**: Want to switch production types
- **Good for**: Market strategy, adapting to resource needs

---

### Submenu Actions

#### (7) Alerts / Notifications → Submenu
**Location**: `command_line.py:186-197`
**Has back button**: ✅ Yes (option 0)

##### (7.0) Back
- Returns to main menu

##### (7.1) Alert Attacks → 701: `alertAttacks()`
- **Purpose**: Get notifications when attacked or about to be attacked
- **When to use**: Want to be warned of incoming military threats
- **Good for**: Defense preparation, avoiding losses, military awareness

##### (7.2) Alert Wine Running Out → 702: `alertLowWine()`
- **Purpose**: Get notified when cities are low on wine
- **When to use**: Have taverns and need wine monitoring
- **Good for**: Preventing happiness drops, maintaining production bonuses

---

#### (8) Marketplace → Submenu
**Location**: `command_line.py:199-210`
**Has back button**: ✅ Yes (option 0)

##### (8.0) Back
- Returns to main menu

##### (8.1) Buy Resources → 801: `buyResources()`
- **Purpose**: Automatically buy resources from marketplace
- **When to use**: Need resources and have gold to spend
- **Good for**: Quick resource acquisition, emergency supplies

##### (8.2) Sell Resources → 802: `sellResources()`
- **Purpose**: Automatically sell resources on marketplace
- **When to use**: Have excess resources and want gold
- **Good for**: Converting surplus to gold, clearing warehouse space

---

#### (9) Donate → Submenu
**Location**: `command_line.py:212-223`
**Has back button**: ✅ Yes (option 0)

##### (9.0) Back
- Returns to main menu

##### (9.1) Donate Once → 901: `donate()`
- **Purpose**: Donate resources to island sawmill or luxury building once
- **When to use**: Want to level up island resource building
- **Good for**: One-time donations, manual control

##### (9.2) Donate Automatically → 902: `donationBot()`
- **Purpose**: Continuously donate resources to max out island buildings
- **When to use**: Want to automate island building upgrades
- **Good for**: Island development, passive contribution to island

---

#### (12) Military Actions → Submenu
**Location**: `command_line.py:237-247`
**Has back button**: ✅ Yes (option 0)

##### (12.0) Back
- Returns to main menu

##### (12.1) Train Army → 1201: `trainArmy()`
- **Purpose**: Automatically train troops and ships in barracks/shipyard
- **When to use**: Want to automate military unit production
- **Good for**: Building armies, maintaining fleet, military buildup

##### (12.2) Send Troops/Ships → 1202: `stationArmy()`
- **Purpose**: Send military units to another city (garrison/occupy)
- **When to use**: Want to move troops between cities or to allies
- **Good for**: Defense reinforcement, troop positioning, occupying colonies

---

#### (19) Attack / Grind Barbarians → Submenu
**Location**: `command_line.py:225-235`
**Has back button**: ✅ Yes (option 0)

##### (19.0) Back
- Returns to main menu

##### (19.1) Simple Attack → 1901: `attackBarbarians()`
- **Purpose**: Perform single attack on barbarian villages
- **When to use**: Want to attack barbarians once for loot
- **Good for**: Manual raiding, testing barbarian strength

##### (19.2) Auto Grind → 1902: `autoBarbarians()`
- **Purpose**: Automatically and continuously attack barbarians
- **When to use**: Want to farm barbarians for resources/experience
- **Good for**: Resource grinding, military XP farming, automated raiding

---

#### (20) Dump / Monitor World → Submenu
**Location**: `command_line.py:249-259`
**Has back button**: ✅ Yes (option 0)

##### (20.0) Back
- Returns to main menu

##### (20.1) Monitor Islands → 2001: `searchForIslandSpaces()`
- **Purpose**: Search for islands with open colony spots
- **When to use**: Looking for new colony locations
- **Good for**: Expansion planning, finding good resource islands

##### (20.2) Dump & Search World → 2002: `dumpWorld()`
- **Purpose**: Download and analyze world data (islands, cities, players)
- **When to use**: Want comprehensive world intelligence
- **Good for**: Strategic planning, finding targets, world mapping

---

#### (21) Options / Settings → Submenu
**Location**: `command_line.py:261-281`
**Has back button**: ✅ Yes (option 0)

##### (21.0) Back
- Returns to main menu

##### (21.1) Configure Proxy → 2101: `proxyConf()`
- **Purpose**: Set up proxy server for Ikabot connections
- **When to use**: Need to route traffic through proxy (privacy/access)
- **Good for**: Privacy, avoiding detection, bypassing restrictions

##### (21.2) Enter/Change Telegram Data → 2102: `updateTelegramData()`
- **Purpose**: Configure Telegram bot for notifications
- **When to use**: Want Telegram notifications from Ikabot
- **Good for**: Mobile alerts, remote monitoring

##### (21.3) Kill Tasks → 2103: `killTasks()`
- **Purpose**: Stop running background tasks
- **When to use**: Need to stop automated processes
- **Good for**: Emergency stop, changing automation, troubleshooting

##### (21.4) Configure Captcha Resolver → 2104: `decaptchaConf()`
- **Purpose**: Set up automatic captcha solving service
- **When to use**: Getting captchas and want automation
- **Good for**: Unattended operation, handling anti-bot measures

##### (21.5) Logs → 2105: `logs()`
- **Purpose**: View Ikabot logs
- **When to use**: Troubleshooting, monitoring activity
- **Good for**: Debugging, tracking automation, auditing actions

##### (21.6) Message Telegram Bot → 2106: `testTelegramBot()`
- **Purpose**: Test Telegram bot connection
- **When to use**: Verifying Telegram integration works
- **Good for**: Setup verification, connection testing

##### (21.7) Import / Export Cookie → 2107: `importExportCookie()`
- **Purpose**: Save or load session cookies
- **When to use**: Want to backup session or move to another machine
- **Good for**: Multi-device usage, session backup, account switching

##### (21.8) Load Custom Module → 2108: `loadCustomModule()`
- **Purpose**: Load user-created custom Ikabot modules
- **When to use**: Have custom functionality to add
- **Good for**: Advanced users, custom automation, extensions

---

## Detailed User Flow Analysis

### Flow Pattern Types

**Type A: Simple Direct Action**
- User selects option → Function executes → Returns to menu
- Example: Get Status (4)

**Type B: Interactive Single-Step**
- User selects option → Function asks for input → Executes → Returns
- Example: Donate Once (9.1)

**Type C: Interactive Multi-Step with Confirmation**
- User selects option → Multiple inputs → Review/Confirm → Execute → Returns
- Example: Send Resources (2)

**Type D: Long-Running Background Task**
- User selects option → Configuration inputs → Start confirmation → Runs in background → Returns to menu
- Example: Auto-Pirate (17)

---

### Example: Auto-Pirate (17) - Detailed Flow

**File**: `ikabot/function/autoPirate.py:21-150`
**Flow Type**: Type D (Multi-step configuration → Background task)

#### Step-by-Step Flow:

1. **Warning Display** (line 35-38)
   - Shows IP exposure warning for captcha solving
   - ❌ **No back button** - User can only Ctrl+C

2. **Input: Pirate Count** (line 40-41)
   ```
   "How many pirate missions should I do? (min = 1)"
   ```
   - Input: Integer >= 1
   - ❌ **No back button** - Cannot return to menu
   - ⚠️ **Point of no return** - User committed after this

3. **Input: Schedule by Time?** (line 42-43)
   ```
   "Should I schedule pirate missions by the time of day? (y/N)"
   ```
   - Input: y/Y/n/N or empty (defaults to No)
   - ❌ **No back button**

4. **If Schedule = Yes** (line 44-91):

   **4a. Choose Daytime Mission** (line 47-59)
   ```
   "Which pirate mission should I do at daytime?"
   (1) 2m 30s
   (2) 7m 30s
   ...
   (9) 16h
   ```
   - Input: 1-9
   - ❌ **No back button** - Cannot go back to schedule question

   **4b. Set Daytime Hours - Start** (line 64-69)
   ```
   "From: "
   ```
   - Input: Hour number or empty (default 10)
   - ❌ **No back button**

   **4c. Set Daytime Hours - End** (line 71-76)
   ```
   "Till: "
   ```
   - Input: Hour number or empty (default 18)
   - ❌ **No back button**

   **4d. Choose Nighttime Mission** (line 78-91)
   ```
   "Which pirate mission should I do at night time?"
   (1) 2m 30s
   ...
   (9) 16h
   ```
   - Input: 1-9
   - ❌ **No back button**

   **4e. Set Nighttime Hours - Start** (line 97-102)
   ```
   "From: "
   ```
   - Input: Hour number or empty (default 19)
   - ❌ **No back button**

   **4f. Set Nighttime Hours - End** (line 104-109)
   ```
   "Till: "
   ```
   - Input: Hour number or empty (default 9)
   - ❌ **No back button**

5. **If Schedule = No** (line 111-126):

   **5a. Choose Single Mission** (similar to step 4a)
   ```
   "Which pirate mission should I do?"
   (1) 2m 30s
   ...
   (9) 16h
   ```
   - Input: 1-9
   - ❌ **No back button**

6. **Final Execution** (line 128+)
   - Task starts in background
   - Returns to main menu
   - ✅ Process runs independently

#### Issues Identified:

| Issue | Severity | Description |
|-------|----------|-------------|
| No early exit | HIGH | After entering pirate count, user cannot back out |
| No back buttons in duration selection | MEDIUM | Cannot return to schedule choice after selecting daytime mission |
| No confirmation step | MEDIUM | No final "Start pirate missions? (y/n)" with summary |
| Ctrl+C handling unclear | LOW | KeyboardInterrupt handling not obvious to user |

---

### Example: Send Resources (2) - Detailed Flow

**File**: `ikabot/function/sendResources.py:17-150`
**Flow Type**: Type C (Multi-step with loop and confirmation)

#### Step-by-Step Flow:

1. **Input: Ship Type** (line 29-38)
   ```
   "What type of ships do you want to use? (Default: Trade ships)"
   (1) Trade ships
   (2) Freighters
   ```
   - Input: 1, 2, or empty (default 1)
   - ❌ **No back button** - Immediate commitment
   - ⚠️ **Point of no return** - Cannot return to main menu without Ctrl+C

2. **Loop: Add Routes** (line 40+)

   **2a. Choose Origin City** (line 43-53)
   ```
   "Origin city:"
   [List of cities with numbers]
   ```
   - Uses `chooseCity(session)` helper
   - ✅ **Ctrl+C handler exists** (line 46-53)
   - If Ctrl+C and routes exist: Asks "Send shipment? [Y/n]"
   - If Ctrl+C and no routes: Returns to main menu
   - ⚠️ **Back button missing** - Should have option 0

   **2b. Choose Destination City** (line 56-57)
   ```
   "Destination city"
   [List of cities OR foreign city option]
   ```
   - Uses `chooseCity(session, foreign=True)`
   - ❌ **No Ctrl+C handler** - Inconsistent with origin
   - ❌ **No back button** - Cannot return to origin selection

   **2c. Enter Resources to Send** (line 89-99+)
   ```
   "Available: Wood:X Wine:Y ..."
   "Send: [for each resource type]"
   ```
   - Multiple inputs (one per resource)
   - ❌ **No back button** - Cannot return to destination selection
   - Must complete all resource inputs

   **2d. Confirm This Route** (implied in code)
   - Route added to list
   - Loop continues or breaks based on user action

3. **Final Confirmation** (line 47-51)
   - Only triggered by Ctrl+C during city selection
   - Shows: "Send shipment? [Y/n]"
   - ✅ **Good pattern** - Gives user final choice

#### Issues Identified:

| Issue | Severity | Description |
|-------|----------|-------------|
| No back at ship type | HIGH | User committed before seeing what function does |
| Inconsistent Ctrl+C handling | HIGH | Only origin has handler, destination doesn't |
| No back in resource input | MEDIUM | Cannot fix destination mistake without Ctrl+C |
| No explicit "Add another route?" | LOW | Loop continuation not clear to user |

---

### Example: Choose City Helper - Detailed Flow

**File**: `ikabot/helpers/pedirInfo.py:101-161`
**Used by**: Almost all functions
**Critical pattern**: No back button mechanism

#### Step-by-Step Flow:

1. **Display Cities** (line 115-150)
   ```
   [If foreign=True]
   0: foreign city

   1: CityName1  (W)
   2: CityName2  (M)
   ...
   ```

2. **Input: Choose City** (line 152-160)
   - If `foreign=True`: Accepts 0-N (where 0 = foreign city)
   - If `foreign=False`: Accepts 1-N (no option 0)
   - ❌ **No back button in non-foreign mode**
   - ⚠️ **Option 0 used for "foreign city", not "back"**

3. **If Foreign City Selected** (line 156-157)
   - Calls `chooseForeignCity(session)`
   - **File**: `pedirInfo.py:163-223`

   **3a. Enter Coordinates** (line 176-177)
   ```
   "coordinate x:"
   "coordinate y:"
   ```
   - Two separate inputs
   - ❌ **No back button** - Cannot return to city list
   - ❌ **No validation until after both inputs** - Wasted time if wrong

   **3b. Validate & Show Foreign Cities** (line 195-218)
   - If invalid coordinates: Loops back to chooseCity
   - Shows list of foreign cities on island
   - ❌ **No back button** - Cannot return to coordinate input

   **3c. Select Foreign City** (line 218)
   - Input: 1-N
   - ❌ **No back button**

#### Issues Identified:

| Issue | Severity | Description |
|-------|----------|-------------|
| No "back" option in standard mode | HIGH | Every function using chooseCity forces commitment |
| Option 0 ambiguity | MEDIUM | In foreign mode, 0 = foreign, not back |
| No back in coordinate entry | MEDIUM | Cannot return to local city list |
| No back in foreign city selection | MEDIUM | Cannot fix coordinate mistake |

---

## Summary of Missing Back Buttons

### High Priority (Function Entry Points)

| Function | Location | Missing Back | Impact |
|----------|----------|--------------|---------|
| `autoPirate` | After pirate count input | ❌ No back | User locked into 6+ more inputs |
| `sendResources` | After ship type input | ❌ No back | User locked into route builder |
| `chooseCity` | All city selections (non-foreign) | ❌ No option 0 | Forces city selection |
| `donate` | After city selection | ❌ No back | Locked into donation |
| `getStatus` | After totals, city selection | ❌ No back | Must view city details |

### Medium Priority (Mid-Flow Steps)

| Function | Location | Missing Back | Impact |
|----------|----------|--------------|---------|
| `autoPirate` | Duration selection | ❌ No back | Cannot return to schedule choice |
| `sendResources` | Destination selection | ❌ No back | Cannot change origin |
| `sendResources` | Resource amount input | ❌ No back | Cannot change destination |
| `chooseForeignCity` | Coordinate input | ❌ No back | Cannot return to city list |
| `chooseForeignCity` | Foreign city selection | ❌ No back | Cannot change coordinates |

### Low Priority (End of Flow)

| Function | Location | Missing Back | Impact |
|----------|----------|--------------|---------|
| `autoPirate` | Nighttime hours | ❌ No back | Almost done anyway |
| Most functions | Final confirmation | ⚠️ Varies | Some have, some don't |

---

## Input Patterns & Types

### Pattern 1: Digit Selection (min/max range)
```python
read(min=1, max=9, digit=True)
```
- **Used in**: Menu selections, numbered choices
- **Validation**: Automatic (re-prompts on invalid)
- **Escape**: None (must enter valid number or Ctrl+C)

### Pattern 2: Yes/No Choice
```python
read(values=["y", "Y", "n", "N", ""])
```
- **Used in**: Confirmations, binary choices
- **Validation**: Must be in value list
- **Escape**: Empty string often allowed (defaults)

### Pattern 3: Integer Input (validation)
```python
read(min=1, digit=True)
```
- **Used in**: Counts, amounts, coordinates
- **Validation**: Automatic (re-prompts on invalid)
- **Escape**: None

### Pattern 4: Free Text Input
```python
read(msg="Enter name:")
```
- **Used in**: Rare (coordinates, custom values)
- **Validation**: Minimal
- **Escape**: None

### Pattern 5: Empty Allowed (default)
```python
read(min=1, max=2, digit=True, empty=True)
```
- **Used in**: Optional inputs with defaults
- **Validation**: If not empty, validates
- **Escape**: Empty returns default

---

## Recommendations for Back Button Implementation

### Priority 1: Entry Point Protection

Add back button (option 0) to:
1. **All `chooseCity()` calls in non-foreign mode**
   - Change to allow 0 = back
   - Return special value (None or exception) to caller
   - Caller handles gracefully

2. **First input of multi-step functions**
   - `autoPirate`: Before pirate count
   - `sendResources`: Before ship type (or after with confirmation)
   - `donate`: At city selection

### Priority 2: Mid-Flow Navigation

Add back button to:
1. **Duration selection in autoPirate**
   - After schedule choice, allow returning
   - After daytime mission, allow returning

2. **Route building in sendResources**
   - After origin, allow returning (or "remove last route")
   - After destination, allow returning to origin

### Priority 3: Confirmation Steps

Add final confirmation to:
1. **All multi-step configurations**
   - Show summary of choices
   - "Start task with these settings? (y/n/back)"
   - Back returns to beginning or previous step

---

## Architecture Notes for Telegram Port

### Current CLI Architecture

**Key Characteristics**:
1. **Synchronous input**: Blocks on `input()` calls
2. **State in call stack**: Navigation state held in function calls
3. **Linear flow**: One function → inputs → return
4. **No session persistence**: Each function is isolated

### Telegram Bot Architecture Needs

**Key Differences**:
1. **Asynchronous input**: Messages arrive as events
2. **State in storage**: Must persist user's position in flow
3. **Non-linear flow**: Messages can come at any time
4. **Session management**: Must track which user is at which step

### Critical Abstraction Points

For minimal changes (per CONTRIBUTING.md), need:

1. **Input Abstraction Layer**
   ```python
   # Current
   choice = read(min=1, max=9, digit=True)

   # Abstracted
   choice = await input_handler.read(min=1, max=9, digit=True)
   # Works for both CLI (input()) and Telegram (wait for message)
   ```

2. **State Machine Wrapper**
   ```python
   # For Telegram: Track where user is in multi-step flow
   user_state = {
       "function": "autoPirate",
       "step": "duration_selection",
       "data": {"pirate_count": 5, "schedule": True}
   }
   ```

3. **Back Button Handler**
   ```python
   # Telegram can use "Back" button in keyboard
   # CLI can use option 0
   if user_input == "back":
       return_to_previous_step()
   ```

---

## Conclusion

### Current State
- **7 submenus** with back buttons (good!)
- **23 direct functions** without back buttons (needs work)
- **Critical helpers** (`chooseCity`, `chooseForeignCity`) have no back option
- **Multi-step functions** (autoPirate, sendResources) have multiple points of no return

### Telegram Port Feasibility
- **Difficulty**: Medium-High
- **Blocking Issues**: State management, async input handling
- **Solvable**: Yes, with abstraction layer
- **Effort**: Requires architectural changes, but can be minimal with right design

### Next Steps
1. Design input abstraction layer (works for CLI + Telegram)
2. Implement state persistence for Telegram sessions
3. Add back button support to critical functions
4. Create Telegram keyboard layouts matching CLI menus

---

**Created**: 2025-11-10
**Analysis Complete**: Yes
**Ready for Implementation**: Architecture design phase needed first
