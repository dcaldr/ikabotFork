# Issue #03 Addendum: Session Data & Process Reconnection

**Status**: Enhancement Proposal
**Related**: issue-03-background-process-restart-COMPREHENSIVE.md
**Component**: Session Data Storage (aesCipher.py, session.py, process.py)

---

## Current Session Data Structure

### What's Saved in `~/.ikabot`

**File**: Encrypted JSON stored per email+password key

**Structure** (from `aesCipher.py:73-117`):

```python
encrypted_data = {
    "shared": {                          # Shared across ALL accounts
        "telegram": {
            "botToken": "xxxxx",
            "chatId": "123456"
        },
        "logLevel": 2                    # Logging level
    },
    "<username>": {                      # Per account (e.g., "player1")
        "<mundo>": {                     # Per world (e.g., "s1")
            "<servidor>": {              # Per server (e.g., "en")
                "processList": [         # ✅ Currently saved
                    {
                        "pid": 12345,
                        "action": "webServer",
                        "date": 1699123456.789,
                        "status": "running on http://127.0.0.1:43527 and http://192.168.1.100:43527"
                    },
                    {
                        "pid": 12346,
                        "action": "autoPirate",
                        "date": 1699123457.123,
                        "status": "Mission 5/10 complete"
                    }
                ],
                "cookies": {             # ✅ Session cookies
                    "gf-token-production": "...",
                    "ikariam": "..."
                }
            }
        }
    }
}
```

### What's in Process List Entry

**Minimal structure** (from `process.py:35-89`):

```python
{
    "pid": int,          # Process ID (e.g., 12345)
    "action": str,       # Function name (e.g., "webServer")
    "date": float,       # Unix timestamp when started
    "status": str        # Free-form status message (updated via session.setStatus())
}
```

**Key limitation**: All detailed info must be crammed into `status` string!

---

## Current "Reconnection" Approach: Parse Status String

### For webServer

**Status string**:
```python
"running on http://127.0.0.1:43527 and http://192.168.1.100:43527"
```

**Extraction** (regex):
```python
port_match = re.search(r'127\.0\.0\.1:(\d+)', status)
port = port_match.group(1)  # "43527"

ip_match = re.findall(r'(\d+\.\d+\.\d+\.\d+)', status)
ips = ip_match  # ["127.0.0.1", "192.168.1.100"]
```

**Pros**:
- ✅ No schema change needed
- ✅ Works with existing code
- ✅ Human-readable status

**Cons**:
- ❌ Fragile (string format changes break it)
- ❌ Limited to what fits in one string
- ❌ Parsing overhead
- ❌ Can't store complex data structures

### For autoPirate

**Status string**:
```python
"Mission 5/10 complete"
```

**Extraction**:
```python
progress = re.search(r'(\d+)/(\d+)', status)
current = int(progress.group(1))  # 5
total = int(progress.group(2))    # 10
```

**But we CAN'T extract**:
- Schedule enabled? (day/night missions)
- Mission type (which duration?)
- Original configuration

---

## Enhanced Approach: Structured Process Details

### Proposal: Add `processDetails` Field

**Add to session data** (same level as `processList`):

```python
{
    "processList": [...],        # Existing - keep for compatibility
    "cookies": {...},
    "processDetails": {          # NEW - keyed by PID
        "12345": {               # webServer
            "action": "webServer",
            "port": 43527,                    # ✅ Dedicated field
            "local_ip": "192.168.1.100",      # ✅ Structured
            "custom_port": False,             # ✅ Original config
            "started_at": 1699123456.789
        },
        "12346": {               # autoPirate
            "action": "autoPirate",
            "missions": {
                "total": 10,
                "completed": 5,               # ✅ Updated each mission
                "remaining": 5
            },
            "schedule": {
                "enabled": True,
                "day_mission": 3,             # ✅ Can resume with same config
                "day_hours": [10, 18],
                "night_mission": 7,
                "night_hours": [19, 9]
            },
            "started_at": 1699123457.123
        },
        "12347": {               # constructionList
            "action": "constructionList",
            "city": {
                "id": "12345",
                "name": "Athens"
            },
            "buildings": [
                {
                    "name": "Academy",
                    "current_level": 3,
                    "target_level": 8,
                    "status": "building"      # ✅ Current building
                },
                {
                    "name": "Barracks",
                    "current_level": 5,
                    "target_level": 10,
                    "status": "pending"       # ✅ Queue status
                }
            ],
            "started_at": 1699123458.456
        }
    }
}
```

### Implementation

**Step 1**: Add helper to save details

```python
# In session.py or new file helpers/processDetails.py

def saveProcessDetails(session, pid, details):
    """Save structured process details"""
    sessionData = session.getSessionData()

    if "processDetails" not in sessionData:
        sessionData["processDetails"] = {}

    sessionData["processDetails"][str(pid)] = {
        "timestamp": time.time(),
        **details
    }

    session.setSessionData(sessionData)

def getProcessDetails(session, pid):
    """Get structured process details"""
    sessionData = session.getSessionData()
    details = sessionData.get("processDetails", {}).get(str(pid))
    return details

def deleteProcessDetails(session, pid):
    """Remove process details when process exits"""
    sessionData = session.getSessionData()
    if "processDetails" in sessionData:
        sessionData["processDetails"].pop(str(pid), None)
        session.setSessionData(sessionData)
```

**Step 2**: Update functions to save details

**webServer** (in `webServer.py` after port is determined):

```python
# After line 294 (port is determined)
def webServer(session, event, stdin_fd, predetermined_input, port=None):
    # ... port selection logic ...

    # Save structured details
    from ikabot.helpers.processDetails import saveProcessDetails
    saveProcessDetails(session, os.getpid(), {
        "action": "webServer",
        "port": int(port),
        "local_ip": local_network_ip,
        "custom_port": config.enable_CustomPort,
        "urls": [
            f"http://127.0.0.1:{port}",
            f"http://{local_network_ip}:{port}" if local_network_ip else None
        ]
    })

    # ... rest of function
```

**autoPirate** (save config at start, update progress in loop):

```python
def autoPirate(session, event, stdin_fd, predetermined_input):
    # ... configuration collection ...

    # Save initial config
    from ikabot.helpers.processDetails import saveProcessDetails
    saveProcessDetails(session, os.getpid(), {
        "action": "autoPirate",
        "missions": {
            "total": pirateCount,
            "completed": 0,
            "remaining": pirateCount
        },
        "schedule": {
            "enabled": pirateSchedule,
            "day_mission": pirateMissionDayChoice if pirateSchedule else None,
            "night_mission": pirateMissionNightChoice if pirateSchedule else None,
            # ... other config
        }
    })

    # In main loop (line 169+)
    while pirateCount > 0:
        # ... do pirate mission ...

        # Update progress
        details = getProcessDetails(session, os.getpid())
        details["missions"]["completed"] += 1
        details["missions"]["remaining"] -= 1
        saveProcessDetails(session, os.getpid(), details)

        pirateCount -= 1
```

**Step 3**: Enhanced reconnection check

**webServer reconnection** (IMPROVED):

```python
from ikabot.helpers.processDetails import getProcessDetails

# Check for existing webServer
running_webservers = [p for p in process_list if p.get("action") == "webServer"]

if running_webservers:
    existing = running_webservers[0]
    existing_pid = existing["pid"]

    # Try to get structured details first
    details = getProcessDetails(session, existing_pid)

    if details:
        # ✅ Have structured data!
        port = details["port"]
        ips = details["urls"]
        print(f"{bcolors.GREEN}✓ WebServer is already running!{bcolors.ENDC}")
        print(f"  PID: {existing_pid}")
        print(f"  Port: {port}")
        for url in ips:
            if url:
                print(f"  {url}")
    else:
        # ❌ Fallback to parsing status string
        status = existing.get("status", "")
        port_match = re.search(r':(\d+)', status)
        if port_match:
            port = port_match.group(1)
            print(f"{bcolors.GREEN}✓ WebServer is already running!{bcolors.ENDC}")
            print(f"  PID: {existing_pid}")
            print(f"  {status}")

    # ... offer options ...
```

---

## Comparison: Minimal vs Enhanced

| Aspect | Minimal (Parse Status) | Enhanced (Structured Details) |
|--------|------------------------|-------------------------------|
| **Schema change** | ❌ None needed | ✅ Add `processDetails` field |
| **Code changes** | ✅ Minimal (just parsing) | ⚠️ Update all 20 functions |
| **Reliability** | ⚠️ Fragile (string parsing) | ✅ Robust (typed fields) |
| **Data richness** | ❌ Limited to status string | ✅ Complex nested structures |
| **Resume capability** | ❌ Can't resume | ✅ Can resume with config |
| **Progress tracking** | ⚠️ Parse from string | ✅ Real-time updates |
| **Backward compat** | ✅ Perfect | ⚠️ Need migration logic |
| **Implementation** | ✅ Quick (1 day) | ⚠️ Longer (1 week) |

---

## Recommendation: Hybrid Approach

### Phase 1: Minimal (Immediate)

Use **status string parsing** for immediate fix:
- webServer: Parse port from status
- autoPirate: Parse mission progress from status
- Offer reconnection options based on parsed info

**Effort**: 1-2 days
**Risk**: Low (no schema change)

### Phase 2: Enhanced (Long-term)

Add **structured `processDetails`**:
- Add field to session data
- Update 5 HIGH-priority functions first:
  - webServer, autoBarbarians, alertLowWine, consolidateResources, investigate
- Migrate remaining 15 functions gradually
- Keep status string for human readability

**Effort**: 1-2 weeks
**Risk**: Medium (schema change, migration needed)

### Benefits of Hybrid

- ✅ Get immediate fix fast (Phase 1)
- ✅ Keep human-readable status in process table
- ✅ Add machine-readable structured data alongside
- ✅ Gradual migration (no big-bang rewrite)
- ✅ Backward compatible (check for details, fall back to parsing)

---

## Example: webServer Hybrid Implementation

**Phase 1** (immediate):
```python
# Parse from status
status = process["status"]
port = extract_port_from_status(status)  # Regex
show_url(f"http://127.0.0.1:{port}")
```

**Phase 2** (enhanced):
```python
# Try structured first, fallback to parsing
details = getProcessDetails(session, pid)
if details and "port" in details:
    port = details["port"]  # ✅ Reliable
else:
    port = extract_port_from_status(process["status"])  # ⚠️ Fallback

show_url(f"http://127.0.0.1:{port}")
```

**Both saved**:
```python
# Status for humans
session.setStatus(f"running on http://127.0.0.1:{port}")

# Details for machines
saveProcessDetails(session, os.getpid(), {
    "port": port,
    "urls": [...]
})
```

---

## What Functions Would Benefit Most

### HIGH Value (save structured details)

1. **webServer**: port, IPs, URLs
2. **autoPirate**: mission config, progress
3. **autoBarbarians**: target selection, attack schedule
4. **buyResources**: target amounts, current progress
5. **sellResources**: sell offers, progress
6. **constructionList**: building queue, current building
7. **trainArmy**: unit types, quantities, progress

### MEDIUM Value

8. **alertLowWine**: threshold settings, monitored cities
9. **consolidateResources**: destination city, schedule
10. **donationBot**: donation targets, schedule

### LOW Value (status string sufficient)

11-20. One-time tasks, simple monitors

---

## Migration Strategy

### Backward Compatibility

**Old sessions** (don't have `processDetails`):
```python
details = getProcessDetails(session, pid)
if details is None:
    # Fallback to parsing status
    details = parse_status_field(process["status"])
```

**New sessions** (have `processDetails`):
```python
details = getProcessDetails(session, pid)
# Use structured data directly
```

### Cleanup on Process Exit

**Update `process.py:updateProcessList()`**:

```python
def updateProcessList(session, programprocesslist=[]):
    # ... existing logic ...

    # Clean up details for dead processes
    from ikabot.helpers.processDetails import getProcessDetails, deleteProcessDetails

    if "processDetails" in sessionData:
        dead_pids = []
        for pid_str in sessionData["processDetails"].keys():
            pid = int(pid_str)
            if pid not in [p["pid"] for p in runningIkabotProcessList]:
                dead_pids.append(pid_str)

        for pid_str in dead_pids:
            deleteProcessDetails(session, int(pid_str))

    return runningIkabotProcessList
```

---

## Conclusion

### Current State
- ✅ Session data DOES exist (`~/.ikabot` encrypted JSON)
- ✅ Already stores `processList` with status strings
- ✅ Already stores shared data (Telegram config)
- ❌ Process details crammed into status string

### Proposed Enhancement
- ✅ Add `processDetails` field alongside `processList`
- ✅ Keep both for hybrid approach (humans read status, code reads details)
- ✅ Gradual migration (5 functions → 20 functions)
- ✅ Backward compatible (fallback to parsing)

### Immediate Action (Phase 1)
**Implement status parsing for webServer reconnection** (as already planned in comprehensive doc)

### Future Enhancement (Phase 2)
**Add structured `processDetails` for robust reconnection and resume capability**

---

**Created**: 2025-11-10
**Related**: issue-03-background-process-restart-COMPREHENSIVE.md
**Recommendation**: Phase 1 immediate, Phase 2 after validation
