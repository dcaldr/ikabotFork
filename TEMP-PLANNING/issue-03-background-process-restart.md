# Issue #03: Background Processes Don't Restart Properly After Session End

**Status**: Confirmed - Architectural Issue
**Priority**: MEDIUM-HIGH
**Platform**: All platforms
**Component**: Process Management (ikabot/helpers/process.py, command_line.py)
**Type**: Architecture Design Limitation

---

## Summary

After ending an ikabot session (closing CLI) and starting a new one, background processes (webServer, autoPirate, constructionList) remain running but cannot be properly restarted or controlled from the new session.

**User Experience**:
- Process shows in table (appears to be running)
- Trying to start same function again either:
  - Fails (webServer: port in use)
  - Starts duplicate process (autoPirate, constructionList)
  - Causes confusion (can't stop/restart)

---

## How Background Processes Work (Current Architecture)

### Process Lifecycle

**Starting a Background Task** (`command_line.py:283-302`):

```python
# User selects menu option (e.g., option 17 = autoPirate)
event = multiprocessing.Event()
process = multiprocessing.Process(
    target=menu_actions[selected],  # e.g., autoPirate function
    args=(session, event, sys.stdin.fileno(), config.predetermined_input),
    name=menu_actions[selected].__name__,
)
process.start()  # New process spawned

# Add to process table
process_list.append({
    "pid": process.pid,
    "action": menu_actions[selected].__name__,
    "date": time.time(),
    "status": "started",
})
updateProcessList(session, programprocesslist=process_list)

event.wait()  # Wait for process to signal it's detached
# Control returns to CLI menu
```

**Background Process Flow** (e.g., `autoPirate.py:165-169`):

```python
def autoPirate(session, event, stdin_fd, predetermined_input):
    # ... user configuration (pirate count, mission type, etc.) ...

    # Detach from parent CLI
    set_child_mode(session)  # Disable SIGINT, mark as child
    event.set()              # Signal parent: "I'm independent now"

    # Main work loop (continues after CLI returns to menu)
    while pirateCount > 0:
        # Do pirate mission
        # Wait for completion
        # Repeat

    # When done, exit
    session.logout()
```

**Process Table Management** (`process.py:35-89`):

```python
def updateProcessList(session, programprocesslist=[]):
    # Read from session file (~/.ikabot)
    sessionData = session.getSessionData()
    fileList = sessionData.get("processList", [])

    # Check which PIDs are still alive
    runningIkabotProcessList = []
    for process in fileList:
        try:
            proc = psutil.Process(pid=process["pid"])
            if proc.name() == ika_process and isAlive:
                runningIkabotProcessList.append(process)
        except psutil.NoSuchProcess:
            # Process died, don't include
            pass

    # Add new processes if provided
    for process in programprocesslist:
        if process not in runningIkabotProcessList:
            runningIkabotProcessList.append(process)

    # Write back to session file
    sessionData["processList"] = runningIkabotProcessList
    session.setSessionData(sessionData)

    return runningIkabotProcessList
```

---

## The Problem: Session Restart Behavior

### What Happens When You Close and Reopen Ikabot

1. **Close ikabot CLI** (Ctrl+C or exit):
   - Main CLI process exits
   - Background processes KEEP RUNNING (by design - they're detached)
   - Process table saved to `~/.ikabot` file

2. **Reopen ikabot CLI**:
   - New main process starts
   - Creates NEW `Session` object (new login, new memory space)
   - Reads process table from `~/.ikabot`
   - Checks PIDs: "These are still alive"
   - Displays them in table

3. **Try to start same function again**:
   - **Problem**: Old process still running
   - **Results**:
     - **WebServer**: Port conflict (detected, prompts for new port)
     - **AutoPirate**: Would start SECOND instance (duplicate)
     - **ConstructionList**: Would start SECOND instance (duplicate)

### Root Cause

**Multiprocessing isolation**:
- Each process has its own memory space
- Old processes have OLD Session object
- New CLI has NEW Session object
- No IPC (inter-process communication) exists

**Cannot**:
- Stop old process from new CLI (no communication channel)
- Reconnect to old process (different Session)
- Resume control of old process (it's independent)

**Can only**:
- See it's running (check PID)
- Kill it via OS (but new CLI doesn't do this automatically)

---

## Affected Functions

### Function-Specific Behavior

#### 1. WebServer (`webServer.py:43-344`)

**Current Behavior**:
- Line 340: `app.run(host="0.0.0.0", port=int(port), threaded=True)`
- Binds to specific port (e.g., 43527)

**Problem on Restart**:
- Old webServer still holds port
- Line 279: Port check detects it's in use
- Line 280: Prompts "Port X is already in use, try another port"
- Line 300: OR auto-increments to next available port

**User Experience**:
```
User: Starts webServer on port 43527
      Closes ikabot CLI
      Reopens ikabot CLI
User: Tries to start webServer again
Bot:  "Port 43527 is already in use, try another port"
User: ??? "But I closed ikabot!"
```

**Why Confusing**:
- User expects webServer to stop when they close CLI
- Port check WORKS but message doesn't explain old process is still running
- Starting on new port works, but now have TWO webServers (old + new)

#### 2. AutoPirate (`autoPirate.py:21-262`)

**Current Behavior**:
- Line 169: `while pirateCount > 0:` - Runs until count reaches 0
- No mechanism to stop mid-way except kill PID

**Problem on Restart**:
- Old autoPirate still running loop
- New CLI session can start ANOTHER autoPirate
- Two separate processes both doing pirate missions

**User Experience**:
```
User: Starts autoPirate (10 missions)
      Closes ikabot CLI after 3 missions
      (7 missions remaining, still running in background)
      Reopens ikabot CLI
      Table shows: autoPirate running
User: Tries to start autoPirate again
Bot:  Starts SECOND autoPirate instance
Result: 2x autoPirate processes competing
```

**Why Problematic**:
- Can't stop/restart the first one
- Can't change configuration of running one
- Starting new one causes duplicates
- Both might try to use same pirate fortress (conflicts)

#### 3. ConstructionList (`constructionList.py:585-704`)

**Current Behavior**:
- Line 695-696: `for building in buildings: expandBuilding(...)`
- Loops through buildings sequentially
- Waits for each construction to complete

**Problem on Restart**:
- Old constructionList still running
- New attempt starts ANOTHER construction list
- May conflict (try to build same building twice)

**User Experience**:
```
User: Starts constructionList (upgrade 5 buildings)
      Closes ikabot CLI after 2 buildings
      (3 buildings remaining, still running)
      Reopens ikabot CLI
      Table shows: constructionList running
User: Wants to add more buildings to queue
      No way to do this - must wait for original to finish
User: Tries to start constructionList again
Bot:  Starts SECOND constructionList
Result: Potential conflicts
```

---

## Why This Happens: Architectural Analysis

### Design Decision: Detached Background Processes

**Intentional Design** (`process.py:15-22`):
```python
def set_child_mode(session):
    """Mark process as detached child"""
    session.padre = False  # Not parent anymore
    deactivate_sigint()    # Ignore Ctrl+C
```

**Benefit**: User can close CLI, processes keep running
**Drawback**: User cannot reconnect or control them later

### Unix vs Windows Behavior

**Unix/Linux**:
- Processes can detach from parent
- Survive terminal closure
- Continue running independently

**Windows**:
- Similar but with caveats
- Closing terminal MAY kill processes (depends on how closed)

**From `command_line.py:307-311`**:
```python
if isWindows:
    print("Closing this console will kill the processes.")
    enter()
```

**Inconsistency**: Documentation says Windows kills processes, but they might survive anyway depending on how terminal is closed.

---

## Current Workarounds

### What Users Can Do Now

#### Option 1: Kill Processes Manually

**Via ikabot menu**:
- Option 21 (Settings) → Option 3 (Kill tasks)
- Shows all running tasks
- Can kill by PID

**Via OS**:
```bash
# Linux/Mac
ps aux | grep ikabot
kill <PID>

# Windows
tasklist | findstr python
taskkill /PID <PID> /F
```

#### Option 2: Use Different Ports (WebServer Only)

- Let ikabot auto-increment to next port
- Now have multiple webServers (wasteful but works)

#### Option 3: Wait for Completion

- Let old process finish naturally
- Then start new one

#### Option 4: Don't Close CLI

- Leave CLI open if you need to control processes
- Defeats purpose of background processes

---

## Proposed Solutions

### Solution 1: Process Control Commands (RECOMMENDED)

**Add IPC mechanism for basic control**:

**Implementation**:
1. Each background process listens on a socket/pipe
2. CLI can send commands: STOP, PAUSE, RESUME, STATUS
3. Process responds and obeys commands

**Example**:
```python
# In background process (autoPirate)
control_socket = socket.socket(AF_UNIX, SOCK_STREAM)
control_socket.bind(f"/tmp/ikabot_{os.getpid()}.sock")

while pirateCount > 0:
    # Check for control commands
    command = check_control_socket(control_socket)
    if command == "STOP":
        break

    # Do pirate mission
    ...

# In CLI (command_line.py)
def send_control_command(pid, command):
    sock = socket.socket(AF_UNIX, SOCK_STREAM)
    sock.connect(f"/tmp/ikabot_{pid}.sock")
    sock.send(command.encode())
    sock.close()
```

**Pros**:
- Can stop/pause/resume from any CLI session
- Clean shutdown
- User-friendly

**Cons**:
- Requires code changes to all background functions
- Cross-platform complexity (Unix sockets vs Windows named pipes)

### Solution 2: Detect and Warn (SIMPLE)

**Add better detection and user messages**:

**For webServer**:
```python
# Before starting webServer
if is_port_in_use(port):
    # Check if it's OUR old webServer
    old_processes = [p for p in updateProcessList(session)
                     if p["action"] == "webServer"]
    if old_processes:
        print(f"⚠️ WebServer is already running (PID: {old_processes[0]['pid']})")
        print("Options:")
        print("  1) Use existing server")
        print("  2) Kill old server and start new one")
        print("  3) Start new server on different port")
        choice = read(min=1, max=3, digit=True)

        if choice == 1:
            print(f"WebServer URL: http://127.0.0.1:{port}")
            return
        elif choice == 2:
            os.kill(old_processes[0]["pid"], signal.SIGTERM)
            time.sleep(2)
        # else: continue with new port
```

**For autoPirate/constructionList**:
```python
# Before starting autoPirate
running_autopirates = [p for p in updateProcessList(session)
                       if p["action"] == "autoPirate"]
if running_autopirates:
    print(f"⚠️ AutoPirate is already running (PID: {running_autopirates[0]['pid']})")
    print("Starting another instance may cause conflicts.")
    print("Options:")
    print("  1) Cancel (let old one finish)")
    print("  2) Kill old one and start fresh")
    print("  3) Start anyway (may conflict)")
    choice = read(min=1, max=3, digit=True)

    if choice == 1:
        return
    elif choice == 2:
        os.kill(running_autopirates[0]["pid"], signal.SIGTERM)
        time.sleep(2)
```

**Pros**:
- Simple to implement
- Minimal code changes
- Better UX immediately

**Cons**:
- Doesn't solve root problem (still manual)
- Still can't control running process

### Solution 3: Process State Persistence (COMPLEX)

**Save process state to disk, allow resume**:

**Implementation**:
1. Background process periodically saves state to file
2. On restart, check for state files
3. Offer to resume from saved state

**Example**:
```python
# In autoPirate
while pirateCount > 0:
    # Save state every iteration
    state = {
        "pirateCount": pirateCount,
        "schedule": schedule,
        "mission_type": pirateMissionChoice,
        # ... other config
    }
    with open(f"/tmp/autopirate_{os.getpid()}.state", "w") as f:
        json.dump(state, f)

    # Do mission
    pirateCount -= 1

# In CLI
state_files = glob.glob("/tmp/autopirate_*.state")
if state_files:
    print("Found interrupted autoPirate session")
    print("Resume? [y/n]")
    if read().lower() == "y":
        # Load state and continue from where it left off
        pass
```

**Pros**:
- Can resume long-running tasks
- Survives crashes/restarts

**Cons**:
- Very complex
- Requires significant refactoring
- State serialization challenges

### Solution 4: Single-Instance Locks (PREVENTIVE)

**Prevent multiple instances of same function**:

**Implementation**:
```python
import fcntl  # Unix
# or msvcrt for Windows

def acquire_lock(function_name):
    """Try to acquire exclusive lock for this function"""
    lock_file = f"/tmp/ikabot_{function_name}.lock"
    try:
        f = open(lock_file, "w")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f  # Keep file open to hold lock
    except IOError:
        return None  # Lock already held

# In each function
def autoPirate(session, event, stdin_fd, predetermined_input):
    lock = acquire_lock("autoPirate")
    if lock is None:
        print("❌ AutoPirate is already running in another process")
        print("Wait for it to finish or kill it first.")
        event.set()
        return

    try:
        # Do work
        ...
    finally:
        lock.close()  # Release lock
```

**Pros**:
- Prevents confusion (can't start duplicates)
- Simple to implement
- Cross-platform (with platform-specific lock implementations)

**Cons**:
- Doesn't solve "can't control" problem
- Just prevents duplicates

---

## Recommendations

### Immediate (Low Effort, High Impact)

**Implement Solution 2: Detect and Warn**

- Add detection in webServer, autoPirate, constructionList
- Offer clear choices to user
- Show which PID is running
- Option to kill old and start new

**Effort**: 1-2 days
**Impact**: Much better UX
**Risk**: Low (just adds checks, doesn't change behavior)

### Short-term (Medium Effort, Medium-High Impact)

**Implement Solution 4: Single-Instance Locks**

- Prevent duplicate processes
- Clear error messages
- Cross-platform lock mechanism

**Effort**: 2-3 days
**Impact**: Eliminates confusion
**Risk**: Low-Medium (need to test lock releases on crashes)

### Long-term (High Effort, High Impact)

**Implement Solution 1: Process Control Commands**

- Full IPC mechanism
- STOP, PAUSE, RESUME commands
- Status queries
- Clean shutdown

**Effort**: 1-2 weeks
**Impact**: Complete solution
**Risk**: Medium (cross-platform IPC is complex)

---

## Testing Plan

### Manual Testing

**Test Scenario 1: WebServer Restart**
1. Start webServer
2. Note port number
3. Close ikabot CLI
4. Reopen ikabot CLI
5. Verify process shows in table
6. Try to start webServer again
7. Verify proper handling (detect + warn)

**Test Scenario 2: AutoPirate Restart**
1. Start autoPirate (10 missions)
2. Close CLI after 3 missions
3. Reopen CLI
4. Verify process shows in table
5. Try to start autoPirate again
6. Verify proper handling (detect + warn)

**Test Scenario 3: Kill from New Session**
1. Start any background task
2. Close CLI
3. Reopen CLI
4. Use Kill Tasks menu
5. Verify process is killed
6. Verify removed from table

### Platform Testing
- [ ] Linux (Ubuntu, Debian)
- [ ] macOS
- [ ] Windows 10/11
- [ ] Raspberry Pi OS

---

## Related Issues

- **Issue #01**: Web server IP detection on Linux (different issue, same component)
- **Issue #02**: AutoPirate bugs (some overlap)
- **Feat #03**: CLI table auto-update (shows outdated process info)

---

## Known Workarounds

For users encountering this issue NOW:

1. **Use Kill Tasks** (Option 21 → 3) before restarting same function
2. **For webServer**: Let it use next available port (wasteful but works)
3. **For long tasks**: Leave CLI open instead of closing it
4. **Manual kill**: `kill <PID>` from OS if needed

---

## User-Facing Documentation Needed

Add to README or user guide:

```
### Background Process Management

When you start a long-running task (AutoPirate, WebServer, etc.),
it runs in the background. You can close the CLI and it will continue.

⚠️ Important: If you close and reopen ikabot, background processes
   keep running but you cannot control them from the new session.

To stop a background process:
1. Go to Options (21) → Kill Tasks (3)
2. Select the process to kill
3. OR use your OS: kill <PID> (Linux/Mac) or taskkill /PID <PID> (Windows)

To avoid conflicts:
- Kill old instance before starting new one
- Or wait for old instance to finish
- WebServer: Will use different port automatically
```

---

## Conclusion

This is a **known limitation** of the current multiprocessing architecture. Background processes are designed to be independent, which means:

✅ **Good**: They survive CLI closure
❌ **Bad**: You can't reconnect/control them later

**Recommended Fix**: Implement "Detect and Warn" (Solution 2) as immediate improvement, then add IPC control (Solution 1) as long-term solution.

**Priority**: MEDIUM-HIGH (affects UX significantly, but workarounds exist)

---

**Created**: 2025-11-10
**Analysis Complete**: Yes
**Recommendation**: Implement Solution 2 (Detect & Warn) immediately, Solution 1 (IPC) as future enhancement
**Effort Estimate**: 1-2 days for Solution 2, 1-2 weeks for Solution 1
