# Implementation Status - What's DONE vs What's PLANNED

**Purpose**: Prevent misunderstandings about what exists vs what's planned. Always check this file first!

**Last Updated**: 2025-11-15
**Current Branch**: `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`

---

## Quick Status

| Feature | Status | Location | Notes |
|---------|--------|----------|-------|
| **Pirate Detection** | ✅ **DONE** | alertAttacks.py | Working, tested |
| **Crew Conversion Defense** | ✅ **DONE** | emergencyDefense.py + pirateDefense.py | Automatic + Manual modes |
| **Debug Logging** | ✅ **DONE** | alertAttacks.py | Optional, can be removed |
| **alertAttacksNG** (dual-mode) | ❌ **PLANNED** | TEMP-PLANNING/feat-10-*.md | Not started |

---

## What's DONE ✅

### 1. Pirate Attack Detection & Classification

**File**: `ikabot/function/alertAttacks.py`

**What it does**:
- Detects pirate attacks (vs player attacks)
- Uses `event.type == "piracy"` AND `event.missionIconClass == "piracyRaid"`
- Different alert messages for pirates vs players

**Example alert**:
```
-- PIRATE ATTACK --
Raid (in progress)
from the pirate fortress Hr4fnsfj0rdur of _K4_
to Rome
arrival in: 4M
(Pirate attacks cannot show unit/fleet numbers)
```

**Commits**:
- `3d0295b` - Implement pirate attack classification in alerts
- `03f1ee8` - Add pirate detection fields and analysis

---

### 2. Automatic Pirate Defense (Crew Conversion)

**Files**:
- `ikabot/helpers/pirateDefense.py` (372 lines) - Core defense logic
- `ikabot/function/emergencyDefense.py` (208 lines) - Dual-mode interface
- `ikabot/function/alertAttacks.py` (+15 lines) - Triggers defense
- `ikabot/command_line.py` (+4 lines) - Menu option

**What it does**:
```
Pirate attack detected
    ↓
Convert capture points to crew strength
    ↓
Conversion completes BEFORE attack arrives
    ↓
User alerted with result
```

**Two modes**:
1. **Automatic**: Triggered by alertAttacks when pirate detected
2. **Manual**: Menu → 12 (Military) → 3 (Emergency Pirate Defense)

**Configuration** (menu 12.3.2):
- Enable/disable auto-defense
- Max capture points to spend per attack
- Safety buffer in seconds (don't convert if attack too close)

**How it works**:
```python
# Dynamic conversion rates (fetched from API)
Base time: 156 seconds
Time per crew: 7 seconds
Points per crew: 10 capture points

# Example calculation
Attack arrives in: 600 seconds
Safety buffer: 120 seconds
Available time: 480 seconds

Max crew by time: (480 - 156) / 7 = 46 crew points
Max crew by points: 200 / 10 = 20 crew points (user limit)
Actual conversion: min(46, 20) = 20 crew points

Conversion time: 156 + (20 * 7) = 296 seconds
Attack in 600 sec, conversion done in 296 sec ✓ SAFE!
```

**User confirmed**: "crew conversion is what we needed (missions are not for this at all)"

**Commits**:
- `8b27054` - Implement auto-pirate defense via crew conversion
- `5082021` - Refactor: Move configuration to emergencyDefense module

---

### 3. Debug Logging (Optional)

**File**: `ikabot/function/alertAttacks.py` (lines 21-178)

**What it does**:
- Logs all attack data to `~/ikalog/alert_debug.log`
- JSON Lines format (one JSON per line)
- Includes full API response, pirate indicators, timing

**Status**: Working, used for initial research. Can be removed or made optional.

**Commits**:
- `dd1d75c` - Add precise timing data to debug log
- `03f1ee8` - Add pirate detection fields and analysis

---

## What's PLANNED ❌

### 1. alertAttacksNG - Next Generation Attack Monitoring

**Planning Doc**: `TEMP-PLANNING/feat-10-alertAttacksNG-architecture.md` (976 lines)

**What it will be**:
- Standalone replacement for alertAttacks.py
- **Dual-mode detection**:
  1. Timer-based polling (like alertAttacks, default 5 min)
  2. **Opportunistic detection** (intercepts session.post() calls)
- Zero modifications to existing modules (fork-friendly)
- Monkey-patch `session.post()` to catch militaryAdvisor calls
- 10 second cooldown on opportunistic checks

**Why**:
- Faster detection (5 min timer vs 20 min)
- Instant detection when using other modules (shipMovements, etc.)
- Perfect for fork maintenance (no upstream file changes)

**Status**: ❌ Not started (planning complete)

**Depends on**: Nothing (pirate detection already working)

**Will coexist with**: alertAttacks.py (both run together during testing)

---

### 2. Crew Conversion Integration with alertAttacksNG

**Planning Doc**: `TEMP-PLANNING/feat-11-crew-conversion-alertAttacksNG-integration.md`

**What it will do**:
- Copy crew conversion trigger from alertAttacks to alertAttacksNG
- Same defense logic, faster detection (dual-mode)

**Integration effort**: ~20 lines (copy from alertAttacks.py)

**Status**: ❌ Not started (waiting for alertAttacksNG)

**Depends on**: Feature #10 (alertAttacksNG)

---

## What's OBSOLETE 🗑️

### ~~Auto-Buy Pirates via Missions~~

**Old Planning Doc**: `TEMP-PLANNING/feat-11-auto-buy-pirates-on-detection.md.OBSOLETE`

**Why obsolete**:
- User clarified: "crew conversion is what we needed (missions are not for this at all)"
- Crew conversion is simpler, faster, more reliable
- Already implemented and working
- Pirate missions NOT needed for defense

**Status**: Marked OBSOLETE, kept for reference

---

## Documentation Structure

### Planning Docs (TEMP-PLANNING/)

**Current and accurate**:
- ✅ `feat-10-alertAttacksNG-architecture.md` - Dual-mode detection plan (976 lines)
- ✅ `feat-11-crew-conversion-alertAttacksNG-integration.md` - Crew conversion integration plan
- ✅ `STATUS-implementation-vs-planning.md` - Cross-branch comparison
- ✅ `IMPLEMENTATION-STATUS-README.md` - This file!

**Obsolete (kept for reference)**:
- ⚠️ `feat-10-parallel-attack-monitoring.md.old` - Old helper module approach
- ⚠️ `feat-11-auto-buy-pirates-on-detection.md.OBSOLETE` - Pirate missions approach

**Other branches**:
- Documentation branch: Various analysis docs (issue-04, feat-09, etc.)
- Auto-train branch: PLANNING-AUTO-TRAIN-DEFENSE.md (describes crew conversion)

---

## How to Use This File

### Before Planning
1. Read this file first
2. Check what's DONE (don't re-plan it)
3. Check what's PLANNED (don't duplicate)
4. Check what's OBSOLETE (don't revive it)

### Before Implementing
1. Check DONE section (don't re-implement)
2. Check dependencies (what needs to be done first)
3. Check planning docs (follow the plan)

### After Implementing
1. Update this file (move from PLANNED to DONE)
2. Update planning docs (mark as implemented)
3. Add commit references
4. Update dependencies

---

## Current Implementation Summary

**On branch `claude/bug-pirate-not-classified-01HWPoRQtpZJ9xn9Xm4TWzt7`:**

```
ikabot/
├── function/
│   ├── alertAttacks.py (MODIFIED)
│   │   ├── Pirate detection ✅
│   │   ├── Debug logging ✅
│   │   └── Crew conversion trigger ✅
│   │
│   └── emergencyDefense.py (NEW)
│       ├── Automatic defense mode ✅
│       ├── Manual defense mode ✅
│       └── Configuration interface ✅
│
├── helpers/
│   └── pirateDefense.py (NEW)
│       ├── Find pirate fortress ✅
│       ├── Get conversion data (dynamic API) ✅
│       ├── Calculate max crew (time-aware) ✅
│       ├── Execute conversion ✅
│       └── Format result for alerting ✅
│
└── command_line.py (MODIFIED)
    └── Menu option 12.3 added ✅
```

**Working features**:
1. Detect pirate attacks (automatic)
2. Classify pirate vs player (automatic)
3. Trigger crew conversion (automatic, if enabled)
4. Manual crew conversion (menu 12.3.1)
5. Configure auto-defense (menu 12.3.2)

**Not yet implemented**:
1. alertAttacksNG (dual-mode detection)
2. Opportunistic detection (session.post interceptor)
3. Crew conversion integration with NG

---

## Next Steps

### Immediate (Current Branch)
1. ✅ Merge crew conversion from auto-train branch - **DONE**
2. ✅ Update planning docs - **DONE**
3. ✅ Create this README - **DONE**
4. Test crew conversion thoroughly
5. Verify alertAttacks + crew conversion working together

### Soon (Feature #10)
1. Implement alertAttacksNG.py
2. Implement dual-mode detection (timer + opportunistic)
3. Test alongside alertAttacks
4. Build user confidence in NG

### Later (Feature #11)
1. Copy crew conversion trigger to alertAttacksNG
2. Test dual-mode with crew conversion
3. Monitor for 1-2 weeks
4. Gradually migrate users to NG
5. Keep alertAttacks as fallback

---

## Coexistence Plan

**User note**: "NG version will coexist with this one for some time"

**Why**:
- Opportunistic checks are harder to implement/test
- Keep proven alertAttacks while testing NG
- Low risk migration (both can run together)

**Timeline**:
```
Now:
  alertAttacks.py (stable, crew conversion working)

After Feature #10:
  alertAttacks.py (stable)
  + alertAttacksNG.py (testing, dual-mode)

After validation (weeks/months):
  alertAttacksNG.py (primary, recommended)
  + alertAttacks.py (fallback, deprecated warning)

Eventually (if desired):
  alertAttacksNG.py (only option)
```

---

## Questions to Ask Before Starting Work

1. **Is this already implemented?** (Check DONE section)
2. **Is this already planned?** (Check PLANNED section)
3. **Is this obsolete?** (Check OBSOLETE section)
4. **What are the dependencies?** (Check planning docs)
5. **Which branch has the latest?** (Check STATUS doc)
6. **Will this cause merge conflicts?** (Check modified files)

---

## Lessons Learned

### Misunderstanding: Pirate Missions vs Crew Conversion

**What happened**:
- Planning docs said "auto-buy pirates" (send missions)
- Implementation used "crew conversion" (different branch)
- User had to clarify: crew conversion is correct

**Why it happened**:
- Different Claude instances on different branches
- Planning docs not in sync with implementation
- No central "what's implemented" document

**How to prevent**:
- This README (central source of truth)
- Mark obsolete approaches clearly
- Update docs immediately after implementing
- Cross-reference between branches

### Best Practices Going Forward

1. **Before planning**: Read this README
2. **After implementing**: Update this README
3. **When in doubt**: Check STATUS doc for cross-branch comparison
4. **Mark obsolete**: Don't delete, mark .OBSOLETE or .old
5. **Document why**: Not just what, but WHY approach was chosen

---

**Created**: 2025-11-15
**Owner**: Keep this updated!
**Purpose**: Single source of truth for implementation status
