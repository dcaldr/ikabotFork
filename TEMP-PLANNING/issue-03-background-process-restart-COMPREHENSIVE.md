# Issue #03: Background Process Restart - Comprehensive Analysis

**Status**: Confirmed - Architectural Limitation
**Priority**: HIGH (affects 20 functions)
**Platform**: All platforms
**Component**: Process Management
**Type**: Architecture Design Issue

---

## Executive Summary

**Problem**: When ikabot CLI session is closed and reopened, background processes remain running but cannot be controlled from the new session. Attempting to restart causes conflicts, duplicates, or confusion.

**Scope**: Affects **ALL 20 background functions** that use `set_child_mode()`

**Impact Severity**:
- **HIGH risk** (5 functions): Duplicates cause actual harm
- **MEDIUM risk** (6 functions): Duplicates waste resources
- **LOW risk** (9 functions): Restarts mostly safe

**Root Cause**: Multiprocessing isolation - no IPC between old processes and new CLI session

---

## All Background Functions - Complete Analysis

### Classification Summary

| Category | Count | Functions |
|----------|-------|-----------|
| **Infinite Loop** (Continuous) | 9 | alertAttacks, alertLowWine, autoBarbarians, consolidateResources, donationBot, loginDaily, searchForIslandSpaces, investigate (auto), webServer |
| **Finite Loop** (Batch Task) | 4 | autoPirate, buyResources, sellResources, trainArmy (repeat) |
| **One-Time** (Single Action) | 7 | attackBarbarians, sendResources, distributeResources, dumpWorld, constructionList, activateMiracle, investigate (study) |

### Complete Function Breakdown

#### HIGH RISK - Duplicates Cause Harm (5 functions)

**1. autoBarbarians** (`autoBarbarians.py`)
- **Loop**: Infinite `while True`
- **Does**: Continuously attacks barbarian villages
- **Restart Issue**: Two instances both attack → double attacks, coordination failure
- **Harm**: Wasted troops, inefficient grinding, timing conflicts

**2. alertLowWine** (`alertLowWine.py`)
- **Loop**: Infinite `while True` (checks every N minutes)
- **Does**: Monitors wine levels, auto-transfers wine when low
- **Restart Issue**: Two instances both send wine ships
- **Harm**: Double shipments waste ships, may oversupply unnecessarily

**3. consolidateResources** (`consolidateResources.py`)
- **Loop**: Infinite `while True` (consolidates every N hours)
- **Does**: Gathers resources from multiple cities to one destination
- **Restart Issue**: Two instances send duplicate shipments
- **Harm**: Wasted ship capacity, excessive resource movement

**4. investigate** (`investigate.py` - auto-experiments mode)
- **Loop**: Infinite `while True` (every 4 hours)
- **Does**: Automatically runs experiments using crystal
- **Restart Issue**: Two instances run duplicate experiments
- **Harm**: Wastes valuable crystal on duplicate research

**5. webServer** (`webServer.py`)
- **Loop**: Infinite `app.run()` (Flask server)
- **Does**: Runs web proxy server on specific port
- **Restart Issue**: Port conflict - old server holds port
- **Harm**: Cannot start on same port, confusing UX, multiple servers running

#### MEDIUM RISK - Duplicates Wasteful (6 functions)

**6. alertAttacks** (`alertAttacks.py`)
- **Loop**: Infinite `while True` (checks every 3 minutes)
- **Does**: Monitors for incoming attacks, sends Telegram alerts
- **Restart Issue**: Duplicate alert messages
- **Harm**: Annoying but not destructive, wasted monitoring resources

**7. buyResources** (`buyResources.py`)
- **Loop**: Finite (exits when purchase quota met)
- **Does**: Buys resources from market until target amount reached
- **Restart Issue**: May over-purchase if restarted mid-execution
- **Harm**: Wasted gold, excess resources

**8. sellResources** (`sellResources.py`)
- **Loop**: Finite (exits when sales complete)
- **Does**: Sells resources to market or creates offers
- **Restart Issue**: May create duplicate sell offers
- **Harm**: Confusion in market, may undersell

**9. donationBot** (`donationBot.py`)
- **Loop**: Infinite `while True` (donates every N minutes)
- **Does**: Automatically donates wood to island building
- **Restart Issue**: Duplicate donations
- **Harm**: Wasteful but island benefits, resource inefficiency

**10. trainArmy** (`trainArmy.py` - repeat mode)
- **Loop**: Finite (repeats N times)
- **Does**: Trains troops/ships repeatedly
- **Restart Issue**: May duplicate training orders
- **Harm**: Wasted resources on excessive units

**11. constructionList** (`constructionList.py`)
- **Loop**: One-time (sequential building queue)
- **Does**: Builds selected buildings sequentially
- **Restart Issue**: May try to build same building twice
- **Harm**: Wasted resources if not detected, game may reject duplicate

#### LOW RISK - Restarts Mostly Safe (9 functions)

**12. autoPirate** (`autoPirate.py`)
- **Loop**: Finite `while pirateCount > 0`
- **Does**: Runs N pirate missions then exits
- **Restart Issue**: Can run simultaneously but independent missions
- **Harm**: Minimal - pirate missions queue naturally in game

**13. attackBarbarians** (`attackBarbarians.py`)
- **Loop**: One-time
- **Does**: Plans and executes single barbarian attack
- **Restart Issue**: Each attack is independent
- **Harm**: None - single action

**14. sendResources** (`sendResources.py`)
- **Loop**: One-time
- **Does**: Sends resources via ships once
- **Restart Issue**: Each shipment is independent
- **Harm**: None - single shipment

**15. distributeResources** (`distributeResources.py`)
- **Loop**: One-time
- **Does**: Distributes resources across cities once
- **Restart Issue**: Each distribution is independent
- **Harm**: None - single distribution

**16. loginDaily** (`loginDaily.py`)
- **Loop**: Infinite `while True` (daily cycle)
- **Does**: Collects daily bonuses, cinema, favor tasks
- **Restart Issue**: Operations are idempotent (can only collect once)
- **Harm**: None - game prevents duplicate collection

**17. dumpWorld** (`dumpWorld.py`)
- **Loop**: One-time
- **Does**: Creates world data dump file
- **Restart Issue**: Each dump is independent
- **Harm**: None - just file overwrite

**18. searchForIslandSpaces** (`searchForIslandSpaces.py`)
- **Loop**: Infinite `while True` (monitors continuously)
- **Does**: Watches islands for colonization opportunities
- **Restart Issue**: Duplicate monitoring/alerts
- **Harm**: Minimal - just duplicate notifications

**19. activateMiracle** (`activateMiracle.py`)
- **Loop**: Conditional (one-time OR finite repeats)
- **Does**: Activates wonder miracles
- **Restart Issue**: Game-limited (can't activate if already active)
- **Harm**: None - game enforces cooldown

**20. activateShrine** (`activateShrine.py`)
- **Loop**: Conditional (finite OR infinite every 70h)
- **Does**: Activates island shrine bonuses
- **Restart Issue**: Favor-limited (can only activate when available)
- **Harm**: None - game enforces availability

---

## The WebServer Attachment Solution

### Current Problem

**WebServer restart flow**:
1. User starts webServer → binds to port 43527
2. User closes CLI → webServer keeps running
3. User reopens CLI → webServer still on port 43527
4. User tries to start webServer again
5. **Port conflict** → error or forced to use port 43528
6. Result: TWO webServers running (43527 + 43528)

### Discovery: Status Field Contains Port!

**Analysis of `webServer.py:336-338`**:
```python
session.setStatus(
    f"""running on http://127.0.0.1:{port} {'and '+'http://' + str(local_network_ip) + ':' + port if local_network_ip else ''}"""
)
```

**Key insight**: The `status` field in process list contains the full URL with port number!

**Process list structure** (from `process.py` and `session.py:42-60`):
```python
{
    "pid": 12345,
    "action": "webServer",
    "date": 1699123456.789,
    "status": "running on http://127.0.0.1:43527 and http://192.168.1.100:43527"
}
```

### Proposed Solution: "Reconnect" Mechanism

Instead of trying to "attach" to the running process (impossible due to multiprocessing isolation), we can provide a **reconnection flow** that extracts and displays existing server info.

#### Implementation for webServer

**Add to `webServer.py` BEFORE starting new server**:

```python
def webServer(session, event, stdin_fd, predetermined_input, port=None):
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    banner()

    # === NEW: Check for existing webServer ===
    process_list = updateProcessList(session)
    running_webservers = [p for p in process_list if p.get("action") == "webServer"]

    if running_webservers and port is None:  # Only check if user didn't specify port
        existing = running_webservers[0]
        existing_pid = existing["pid"]
        existing_status = existing.get("status", "")

        # Extract port from status
        port_match = re.search(r'127\.0\.0\.1:(\d+)', existing_status)
        if port_match:
            existing_port = port_match.group(1)
            print(f"{bcolors.GREEN}✓ WebServer is already running!{bcolors.ENDC}")
            print(f"  PID: {existing_pid}")
            print(f"  {existing_status}\n")

            print("What would you like to do?")
            print("  (1) Use existing server (recommended)")
            print("  (2) Kill existing and start fresh")
            print("  (3) Start new server on different port")
            print("  (0) Cancel")

            choice = read(min=0, max=3, digit=True)

            if choice == 0:
                event.set()
                return
            elif choice == 1:
                # Just show info and exit
                print(f"\n{bcolors.BLUE}Using existing webServer:{bcolors.ENDC}")
                print(f"  {existing_status}")
                print("\nYou can access it from your browser now.")
                enter()
                event.set()
                return
            elif choice == 2:
                # Kill existing and continue to start new one
                print(f"\nKilling existing webServer (PID: {existing_pid})...")
                try:
                    import signal
                    os.kill(existing_pid, signal.SIGTERM)
                    time.sleep(2)  # Wait for graceful shutdown
                    print(f"{bcolors.GREEN}✓ Stopped existing webServer{bcolors.ENDC}")
                except Exception as e:
                    print(f"{bcolors.RED}Failed to kill process: {e}{bcolors.ENDC}")
                    print("You may need to kill it manually.")
                    enter()
                    event.set()
                    return
            elif choice == 3:
                # Continue to start on different port (fall through)
                print("\nStarting new webServer on different port...")
                pass
    # === END NEW CODE ===

    # Original webServer logic continues...
    try:
        import flask
        # ... rest of original code
```

**Benefits**:
- ✅ No duplicate webServers
- ✅ User can choose to use existing (most common case)
- ✅ Can kill and restart if needed
- ✅ Can run multiple on different ports if intentional
- ✅ Clear UX with explicit choices

#### Generic "Reconnect" Pattern for Other Functions

**For functions with stored state in status field**:

```python
def check_and_handle_existing_process(session, function_name, allow_duplicates=False):
    """
    Generic function to check for existing process and offer options

    Returns:
        - None: Continue with new process
        - "cancel": User cancelled
        - "use_existing": User wants to keep using existing
    """
    process_list = updateProcessList(session)
    running = [p for p in process_list if p.get("action") == function_name]

    if not running:
        return None  # No existing process, continue

    existing = running[0]
    print(f"{bcolors.WARNING}⚠ {function_name} is already running (PID: {existing['pid']}){bcolors.ENDC}")
    print(f"  Status: {existing.get('status', 'running')}")

    if not allow_duplicates:
        print("\n{bcolors.RED}Running multiple instances may cause conflicts!{bcolors.ENDC}")

    print("\nOptions:")
    print("  (1) Cancel (let existing finish)")
    print("  (2) Kill existing and start fresh")
    if allow_duplicates:
        print("  (3) Start anyway (run both)")

    max_choice = 3 if allow_duplicates else 2
    choice = read(min=1, max=max_choice, digit=True)

    if choice == 1:
        return "cancel"
    elif choice == 2:
        try:
            import signal
            os.kill(existing["pid"], signal.SIGTERM)
            time.sleep(2)
            print(f"{bcolors.GREEN}✓ Stopped existing process{bcolors.ENDC}")
            return None  # Continue with new process
        except Exception as e:
            print(f"{bcolors.RED}Failed to kill: {e}{bcolors.ENDC}")
            return "cancel"
    elif choice == 3:
        return None  # User wants to run both
```

**Usage example in `autoBarbarians.py`**:

```python
def autoBarbarians(session, event, stdin_fd, predetermined_input):
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input
    banner()

    # Check for existing process
    result = check_and_handle_existing_process(session, "autoBarbarians", allow_duplicates=False)
    if result == "cancel":
        event.set()
        return

    # Continue with normal flow...
```

---

## Extracting Information from Process Status

### What's Available in Status Field

Different functions store different information in their status:

**webServer**:
```
"running on http://127.0.0.1:43527 and http://192.168.1.100:43527"
```
- Can extract: port number, local IP

**autoPirate**:
```
"Mission 5/10 complete"
```
- Can extract: progress count

**constructionList**:
```
"Waiting until Nov 10 14:30, Academy 3 -> 4 in Athens, final lvl: 8"
```
- Can extract: current building, city, target level, ETA

**alertAttacks**:
```
"Monitoring attacks"
```
- Generic status

### Status Parsing Utility

**Add to `helpers/process.py`**:

```python
def parse_process_status(action, status):
    """
    Parse status field to extract useful information

    Returns dict with parsed fields specific to each function
    """
    parsed = {"raw": status}

    if action == "webServer":
        # Extract port and IPs
        port_match = re.search(r':(\d+)', status)
        if port_match:
            parsed["port"] = port_match.group(1)

        ip_matches = re.findall(r'(\d+\.\d+\.\d+\.\d+)', status)
        if ip_matches:
            parsed["ips"] = ip_matches

    elif action == "autoPirate":
        # Extract mission progress
        progress_match = re.search(r'(\d+)/(\d+)', status)
        if progress_match:
            parsed["current"] = int(progress_match.group(1))
            parsed["total"] = int(progress_match.group(2))

    elif action == "constructionList":
        # Extract building info
        building_match = re.search(r'(\w+) (\d+) -> (\d+) in (\w+)', status)
        if building_match:
            parsed["building"] = building_match.group(1)
            parsed["from_level"] = int(building_match.group(2))
            parsed["to_level"] = int(building_match.group(3))
            parsed["city"] = building_match.group(4)

    # Add more parsers for other functions as needed

    return parsed
```

---

## Process Reconnection Patterns

### Pattern 1: URL-Based Reconnection (webServer)

**Scenario**: User can access running service via URL

**Implementation**:
1. Extract URL from status
2. Display to user
3. User can visit URL without restarting

**Applies to**: webServer

### Pattern 2: Progress Display (monitoring tasks)

**Scenario**: User wants to see progress of running task

**Implementation**:
1. Extract progress from status
2. Display current state
3. Offer to let it continue or restart

**Applies to**: autoPirate, buyResources, sellResources, trainArmy, constructionList

### Pattern 3: Duplicate Prevention (dangerous tasks)

**Scenario**: Running duplicate would cause harm

**Implementation**:
1. Detect existing process
2. Block new start with clear explanation
3. Offer to kill existing if needed

**Applies to**: autoBarbarians, alertLowWine, consolidateResources, investigate (auto)

### Pattern 4: Duplicate Warning (wasteful tasks)

**Scenario**: Duplicate is wasteful but not catastrophic

**Implementation**:
1. Detect existing process
2. Warn user about waste
3. Allow override if user insists

**Applies to**: alertAttacks, donationBot, buyResources, sellResources

### Pattern 5: Allow Duplicates (safe tasks)

**Scenario**: Multiple instances can coexist safely

**Implementation**:
1. Detect existing process (informational)
2. Note it's already running
3. Allow new start without blocking

**Applies to**: loginDaily, searchForIslandSpaces, dumpWorld, one-time tasks

---

## Implementation Priority

### Phase 1: Immediate (1-2 days)

**Critical fixes for HIGH risk functions**:

1. **webServer**: Add reconnection mechanism (extract URL, offer use existing)
2. **autoBarbarians**: Add duplicate prevention
3. **consolidateResources**: Add duplicate prevention
4. **alertLowWine**: Add duplicate prevention
5. **investigate**: Add duplicate prevention (auto mode)

### Phase 2: Short-term (2-3 days)

**Improvements for MEDIUM risk functions**:

6. **alertAttacks**: Add duplicate warning
7. **buyResources**: Add duplicate warning + progress display
8. **sellResources**: Add duplicate warning + progress display
9. **donationBot**: Add duplicate warning
10. **trainArmy**: Add duplicate warning
11. **constructionList**: Add duplicate prevention + progress display

### Phase 3: Enhancement (1 week)

**Add status parsing and display for all functions**:

12. Create `parse_process_status()` utility
13. Update process table to show parsed status
14. Add "View running tasks" command with detailed info

---

## Testing Plan

### Test Scenario Matrix

| Function | Test: Start while running | Expected Behavior |
|----------|--------------------------|-------------------|
| **webServer** | Try to start again | Detect, show URL, offer options |
| **autoBarbarians** | Try to start again | Block with error, offer to kill existing |
| **alertLowWine** | Try to start again | Block with error, offer to kill existing |
| **consolidateResources** | Try to start again | Block with error, offer to kill existing |
| **investigate** | Try to start again | Block with error, offer to kill existing |
| **alertAttacks** | Try to start again | Warn, allow override |
| **buyResources** | Try to start again | Warn + show progress, allow override |
| **sellResources** | Try to start again | Warn + show progress, allow override |
| **donationBot** | Try to start again | Warn, allow override |
| **trainArmy** | Try to start again | Warn + show progress, allow override |
| **constructionList** | Try to start again | Block + show progress, offer to kill |
| **autoPirate** | Try to start again | Inform + show progress, allow new |
| **loginDaily** | Try to start again | Inform, allow new |
| All one-time tasks | Try to start again | Allow (independent executions) |

### Manual Test Steps

**For each function**:
1. Start function, wait for it to detach (event.set)
2. Return to main menu (process shows in table)
3. Exit ikabot CLI (Ctrl+D or option 0)
4. Reopen ikabot CLI
5. Verify process still shows in table
6. Try to start same function again
7. **Verify proper handling** (based on expected behavior above)

### Platform Testing
- [ ] Linux (Ubuntu 22.04, Debian)
- [ ] macOS (Intel and Apple Silicon)
- [ ] Windows 10/11
- [ ] Raspberry Pi OS

---

## Recommendations Summary

### Immediate Actions

1. **Implement webServer reconnection** (highest impact, most common)
   - Extract port from status
   - Show URL to user
   - Offer use existing / kill / new port

2. **Add duplicate prevention for HIGH risk functions** (prevent harm)
   - autoBarbarians, alertLowWine, consolidateResources, investigate
   - Block new start
   - Clear error message
   - Offer to kill existing

3. **Update documentation** (help users NOW)
   - Add section on background process behavior
   - Explain "already running" scenarios
   - Document manual kill process

### Long-term Solutions

4. **IPC mechanism for process control** (complete solution)
   - Add socket/pipe communication
   - Commands: STOP, PAUSE, RESUME, STATUS
   - Control from any CLI session
   - Effort: 1-2 weeks

5. **Enhanced process table** (better visibility)
   - Parse and display status info
   - Show progress, URLs, ETAs
   - Color-code by risk level
   - Effort: 3-4 days

---

## User Impact

### Before Fix
- ❌ Confusion when trying to restart
- ❌ Duplicate processes cause harm
- ❌ Wasted resources
- ❌ Port conflicts
- ❌ No visibility into running tasks

### After Phase 1
- ✅ Clear detection of existing processes
- ✅ Smart handling per function risk level
- ✅ webServer reconnection (no duplicates)
- ✅ Prevention of harmful duplicates
- ✅ User-friendly choices

### After Phase 3
- ✅ Full process control from any session
- ✅ Rich status display with parsed info
- ✅ Progress tracking for batch tasks
- ✅ Professional UX

---

**Created**: 2025-11-10
**Analysis Complete**: Yes
**Functions Analyzed**: 20/20
**Priority**: HIGH (affects all background operations)
**Recommendation**: Implement Phase 1 immediately (webServer + HIGH risk prevention)
