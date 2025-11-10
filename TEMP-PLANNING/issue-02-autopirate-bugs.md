# Issue #02: AutoPirate Bugs and Issues

**Status**: Identified, Pending Fix
**Severity**: High (Critical Bug) + Medium (Logic Issues)
**Platform**: All platforms
**Component**: AutoPirate (ikabot/function/autoPirate.py)
**Type**: Multiple bugs and design issues

---

## Summary

The autoPirate module has several bugs and design issues:
1. **CRITICAL**: Hardcoded building position causes failures
2. **HIGH**: Missing null check causes crashes
3. **MEDIUM**: Poor error handling masks problems
4. **LOW**: Suboptimal city selection logic

---

## Question: Should Pirate Fortress Be in Capital?

**Answer: NO** - The pirate fortress is NOT a capital-only building in Ikariam.

### Capital-Only Buildings in Ikariam:
- Palace
- Ambrosia Fountain
- Workshop (in some game versions)

### Non-Capital Buildings (Can Be Anywhere):
- Pirate Fortress ✓
- Temple
- Shrine
- Barracks
- Port
- etc.

**Current Implementation**: The code correctly allows pirate fortress in ANY city, not just capital. This is the correct behavior.

---

## Bug #1: Hardcoded Building Position (CRITICAL)

### Location
**File**: `ikabot/function/autoPirate.py`
**Lines**: 193, 201, 229, 355, 379

### Problem
The code hardcodes `position=17` for the pirate fortress in all API calls, but the pirate fortress can be built at different positions.

### Code Analysis

**Finding the fortress (lines 335-342):**
```python
for pos, building in enumerate(city["position"]):
    if (
        building["building"] == "pirateFortress"
        and building["level"] >= piracyMissionToBuildingLevel[pirateMissionChoice]
    ):
        piracyCities.append(city)  # ❌ Doesn't store 'pos'!
        break
```

**Using the fortress (line 193):**
```python
url = "view=pirateFortress&cityId={}&position=17&..."  # ❌ Hardcoded!
```

**Using the fortress (line 201):**
```python
url = "action=PiracyScreen&function=capture&...&position=17&..."  # ❌ Hardcoded!
```

**Using the fortress (line 229):**
```python
"position": "17",  # ❌ Hardcoded!
```

**Using the fortress (line 379):**
```python
"position": "17",  # ❌ Hardcoded!
```

### How Other Modules Do It Correctly

**Example: activateShrine.py (lines 38-43):**
```python
for pos, building in enumerate(city["position"]):
    if building["building"] == "shrineOfOlympus":
        shrineCity = city_id
        shrinePos = pos  # ✅ Stores the actual position!
        return (shrineCity, shrinePos, ...)
```

**Example: constructBuilding.py (lines 122):**
```python
params = {
    ...
    "position": option["position"],  # ✅ Uses actual position!
    ...
}
```

### Impact
- **Severity**: CRITICAL
- **Effect**: AutoPirate will FAIL if pirate fortress is not at position 17
- **Error**: API calls will fail or target wrong building
- **Frequency**: Affects any user whose pirate fortress is not at position 17
- **Workaround**: None for end users

### Root Cause
1. Code finds the fortress and gets `pos` variable
2. Code correctly adds city to list
3. Code FAILS to store the position value
4. Code uses hardcoded position in all subsequent API calls

---

## Bug #2: Missing Null Check on Regex (HIGH)

### Location
**File**: `ikabot/function/autoPirate.py`
**Lines**: 365-366 (in `convertCapturePoints` function)

### Problem
If regex match fails, the code will crash with `AttributeError`.

### Code Analysis
```python
html = session.post(params=params)
rta = re.search(r'\\"capturePoints\\":\\"(\d+)\\"', html)
capturePoints = int(rta.group(1))  # ❌ Crashes if rta is None!
```

### Impact
- **Severity**: HIGH
- **Effect**: Crashes the autoPirate process
- **Error**: `AttributeError: 'NoneType' object has no attribute 'group'`
- **Frequency**: Rare but possible if HTML format changes or API error
- **Workaround**: None

### When It Happens
- Server returns unexpected HTML format
- API changes
- Network error returns error page
- Session expires during operation

### Correct Pattern
```python
html = session.post(params=params)
rta = re.search(r'\\"capturePoints\\":\\"(\d+)\\"', html)
if rta is None:
    # Handle error - log, raise exception, or use default value
    raise Exception("Failed to find capture points in response")
capturePoints = int(rta.group(1))
```

---

## Bug #3: Bare Except Clause (MEDIUM)

### Location
**File**: `ikabot/function/autoPirate.py`
**Lines**: 396-397 (in `getCurrentMissionWaitingTime` function)

### Problem
Bare `except:` catches all exceptions and silently returns hardcoded 10 minutes.

### Code Analysis
```python
def getCurrentMissionWaitingTime(html):
    try:
        match = re.search(r'ongoingMissionTimeRemaining\\":(\d+),', html)
        assert (
            match
        ), "Couldn't find remaining ongoing mission time, did you run a pirate mission manually?"
        return int(match.group(1))
    except:  # ❌ Catches EVERYTHING, including KeyboardInterrupt, SystemExit!
        return 10 * 60
```

### Impact
- **Severity**: MEDIUM
- **Effect**: Masks errors, makes debugging difficult
- **Error**: None (silently returns wrong value)
- **Frequency**: Only when regex fails
- **Workaround**: Check logs (but there are no logs for this!)

### Issues
1. Catches `KeyboardInterrupt` - user can't interrupt
2. Catches `SystemExit` - program can't exit cleanly
3. Catches unexpected errors - masks programming bugs
4. No logging - impossible to diagnose
5. Returns arbitrary value - 10 minutes may be wrong

### Correct Pattern
```python
def getCurrentMissionWaitingTime(html):
    try:
        match = re.search(r'ongoingMissionTimeRemaining\\":(\d+),', html)
        if match is None:
            logger.warning("Couldn't find remaining ongoing mission time")
            return 10 * 60  # Default fallback
        return int(match.group(1))
    except (ValueError, AttributeError) as e:
        logger.error(f"Error parsing mission time: {e}")
        return 10 * 60
```

---

## Issue #4: Suboptimal City Selection (LOW)

### Location
**File**: `ikabot/function/autoPirate.py`
**Lines**: 188, 224, 257 - Always uses `piracyCities[0]["id"]`

### Problem
Code always uses the FIRST city with a pirate fortress, with no prioritization logic.

### Code Analysis
```python
piracyCities = getPiracyCities(session, pirateMissionChoice)
# ... later ...
html = session.post(city_url + str(piracyCities[0]["id"]))  # ❌ Always first city
```

### Current Behavior
- Gets ALL cities with pirate fortress
- Sorts by... (no explicit sort, so order depends on `getIdsOfCities()`)
- Always picks first in list
- No consideration for:
  - Capital vs non-capital
  - Fortress level (beyond minimum)
  - City resources
  - Distance or location
  - User preference

### Impact
- **Severity**: LOW
- **Effect**: Suboptimal but functional
- **Error**: None
- **Frequency**: Always, but only matters if user has multiple fortresses
- **Workaround**: User can destroy other fortresses or accept behavior

### Comparison: Other Modules

**loginDaily.py** - Iterates all cities to find capital (fountain):
```python
for id in ids:
    html = session.post(city_url + str(id))
    if 'class="fountain' in html:  # is capital
        # Use this city
```

**donationBot.py** - Lets user configure each city individually

**activateShrine.py** - Returns first shrine found (similar behavior)

### Potential Improvements
1. **Prioritize capital** - Use capital's fortress first (if it exists)
2. **Highest level** - Use highest level fortress
3. **User choice** - Ask user which city to use
4. **Round robin** - Rotate between cities
5. **Most points** - Use city with most capture points

### Is This a Bug?
**NO** - This is working as designed, just not optimally. It's a design choice that could be improved but isn't incorrect.

---

## Issue #5: No Validation of Fortress Status (LOW)

### Location
**File**: `ikabot/function/autoPirate.py`
**Lines**: 336-340 (in `getPiracyCities` function)

### Problem
Code doesn't check if the pirate fortress is accessible/usable.

### Code Analysis
```python
if (
    building["building"] == "pirateFortress"
    and building["level"] >= piracyMissionToBuildingLevel[pirateMissionChoice]
):
    piracyCities.append(city)  # ❌ No check if fortress is under construction
```

### Missing Checks
1. Is fortress under construction/upgrading?
2. Is fortress damaged (after attack)?
3. Is city occupied by enemy?
4. Does city have required resources?

### Impact
- **Severity**: LOW
- **Effect**: May fail mission start, but errors are handled
- **Error**: API error or mission failure
- **Frequency**: Rare (only during construction/attack)
- **Workaround**: Wait for construction to finish

### Potential Checks
```python
if (
    building["building"] == "pirateFortress"
    and building["level"] >= piracyMissionToBuildingLevel[pirateMissionChoice]
    and not building.get("isBusy", False)  # Not upgrading
    and building.get("level", 0) > 0  # Not destroyed
):
    piracyCities.append(city)
```

---

## Issue #6: Redundant API Call (TRIVIAL)

### Location
**File**: `ikabot/function/autoPirate.py`
**Line**: 224

### Problem
After captcha failure, makes redundant city view call.

### Code Analysis
```python
for i in range(20):
    # ... try captcha ...
    if captcha == "Error":
        time.sleep(5)
        continue
    session.post(city_url + str(piracyCities[0]["id"]))  # ❌ Why?
    params = { ... }
    html = session.post(params=params, noIndex=True)
```

### Impact
- **Severity**: TRIVIAL
- **Effect**: Extra unnecessary network call
- **Performance**: Negligible (one extra HTTP request)

### Explanation
Comment on line 189 says: "this is needed because for some reason you need to look at the town..."

This might be a workaround for an API quirk, or it might be unnecessary. Not clear without testing.

---

## Related Files

- **Primary**: `ikabot/function/autoPirate.py` (all bugs)
- **Comparison**: `ikabot/function/activateShrine.py:38-43` (correct position handling)
- **Comparison**: `ikabot/function/constructBuilding.py:101-122` (correct position handling)
- **Comparison**: `ikabot/function/loginDaily.py:313-320` (capital detection)

---

## Recommended Fixes

### Priority 1: Fix Critical Bug
1. **Bug #1**: Store and use actual pirate fortress position
   - Modify `getPiracyCities()` to return position along with city
   - Update all API calls to use actual position
   - Test with fortress at different positions

### Priority 2: Fix High Severity Bug
2. **Bug #2**: Add null check for regex match
   - Check if `rta is None` before calling `.group()`
   - Log error and handle gracefully
   - Consider raising exception if critical

### Priority 3: Improve Error Handling
3. **Bug #3**: Replace bare except clause
   - Use specific exception types
   - Add proper logging
   - Don't catch KeyboardInterrupt or SystemExit

### Priority 4: Optional Improvements
4. **Issue #4**: Add city prioritization (optional)
   - Consider adding capital preference
   - Or let user choose city
5. **Issue #5**: Add fortress status validation (optional)
6. **Issue #6**: Remove redundant API call if not needed (test first)

---

## Testing Plan

### Test Cases for Bug #1 (Position)
- [ ] Fortress at position 0
- [ ] Fortress at position 17 (current assumed position)
- [ ] Fortress at different positions (1-16, 18+)
- [ ] Multiple fortresses in different cities at different positions
- [ ] Fortress moved/rebuilt at different position

### Test Cases for Bug #2 (Regex)
- [ ] Normal operation (regex matches)
- [ ] Server returns error page
- [ ] Session expires during operation
- [ ] HTML format changes
- [ ] Network error during request

### Test Cases for Bug #3 (Error Handling)
- [ ] Verify KeyboardInterrupt works
- [ ] Verify proper error logging
- [ ] Check behavior when mission time not found

### Test Cases for Issue #4 (City Selection)
- [ ] Single fortress
- [ ] Multiple fortresses in different cities
- [ ] Fortress in capital vs non-capital
- [ ] Different fortress levels

---

## Timeline

- **Discovered**: 2025-11-10
- **Analyzed**: 2025-11-10
- **Fix Planned**: TBD
- **Fix Implemented**: TBD
- **Released**: TBD

---

## Notes

- Bug #1 is CRITICAL and should be fixed immediately
- Bug #2 and #3 are important for stability
- Issues #4, #5, #6 are minor improvements
- The pirate fortress does NOT need to be in capital (this is correct)
- Current city selection logic is functional but could be improved
