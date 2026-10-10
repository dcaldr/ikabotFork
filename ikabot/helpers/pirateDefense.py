#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helper module for automatic pirate defense via crew conversion.

When a pirate attack is detected, this module:
1. Fetches current capture points available
2. Preserves the passive +1400 crew strength bonus (7000 CP threshold) if applicable
3. Calculates max crew points that can be converted before the attack arrives
4. Converts capture points to crew strength BEFORE attack arrives
5. Returns result for alerting the user

Critical timing constraint: Conversion MUST complete before attack arrives.
"""

import re
import json
import time
import traceback

from ikabot.config import actionRequest
from ikabot.helpers.getJson import getCity
from ikabot.helpers.pedirInfo import getIdsOfCities
from ikabot.helpers.varios import daysHoursMinutes

# Ikariam piracy game constants (1x speed server base)
PIRACY_POINTS_PER_CREW = 10
PIRACY_TIME_PER_CREW = 7
PIRACY_BASE_CONVERSION_TIME = 156  # 2m 36s base conversion startup time
PIRACY_BONUS_THRESHOLD = 7000     # 7000 CP gives +1400 crew strength bonus
PIRACY_BONUS_CREW = 1400          # Passive bonus provided by threshold


def get_pirate_fortress_city(session, target_city_id=None):
    """
    Find a city with a pirate fortress.
    
    In Ikariam, incoming pirate raids can ONLY target cities that have a pirate fortress.
    If target_city_id is provided, we check that city first (or return it if valid).
    Otherwise, we check the session cache, and only crawl cities if not cached.

    Parameters
    ----------
    session : ikabot.web.session.Session
    target_city_id : str or int, optional
        Target city of the pirate raid

    Returns
    -------
    city : dict or None
        City dict with pirate fortress, or None if no fortress found
    """
    try:
        session_data = session.getSessionData()
        
        def _check_city_for_fortress(html_text, cid):
            if "pirateFortress" not in html_text:
                return None
            try:
                # Fast extract backgroundData JSON from response
                bg_match = re.search(r'"updateBackgroundData",\s?([\s\S]*?)\],\["updateTemplateData"', html_text)
                if bg_match:
                    bg_data = json.loads(bg_match.group(1), strict=False)
                    for pos, building in enumerate(bg_data.get("position", [])):
                        if building.get("building") == "pirateFortress":
                            return {
                                "id": str(cid),
                                "islandId": bg_data.get("islandId", 0),
                                "fortress_pos": pos,
                                "fortress_level": building.get("level", 0)
                            }
            except Exception:
                pass
            return {"id": str(cid), "islandId": 0, "fortress_pos": 17, "fortress_level": 1}

        # 1. If target_city_id is provided, verify it directly
        if target_city_id:
            html = session.get(f"?view=city&cityId={target_city_id}")
            fortress = _check_city_for_fortress(html, target_city_id)
            if fortress:
                if session_data.get("pirate_fortress_city_id") != fortress["id"]:
                    session_data["pirate_fortress_city_id"] = fortress["id"]
                    session.setSessionData(session_data)
                return fortress

        # 2. Check cached fortress city ID
        cached_city_id = session_data.get("pirate_fortress_city_id")
        if cached_city_id:
            html = session.get(f"?view=city&cityId={cached_city_id}")
            fortress = _check_city_for_fortress(html, cached_city_id)
            if fortress:
                return fortress

        # 3. Fallback: Scan cities once and cache
        city_ids = getIdsOfCities(session)[0]
        for city_id in city_ids:
            html = session.get(f"?view=city&cityId={city_id}")
            fortress = _check_city_for_fortress(html, city_id)
            if fortress:
                session_data["pirate_fortress_city_id"] = fortress["id"]
                session.setSessionData(session_data)
                return fortress

        return None
    except Exception as e:
        print(f"Error finding pirate fortress: {e}")
        return None


def get_conversion_data(session, city):
    """
    Fetch pirate fortress conversion status from API.

    Parameters
    ----------
    session : ikabot.web.session.Session
    city : dict
        City with pirate fortress

    Returns
    -------
    data : dict or None
        {
            "capture_points": int,
            "base_time_seconds": int,
            "time_per_crew": int,
            "points_per_crew": int,
            "conversion_in_progress": bool
        }
    """
    try:
        params = {
            "view": "pirateFortress",
            "activeTab": "tabCrew",
            "cityId": city["id"],
            "position": city.get("fortress_pos", 17),
            "backgroundView": "city",
            "currentCityId": city["id"],
            "templateView": "pirateFortress",
            "actionRequest": actionRequest,
            "ajax": 1,
        }

        html = session.post(params=params)

        # Extract current capture points
        match = re.search(r'capturePoints[\\"\s:]+(\d+)', html)
        capture_points = int(match.group(1)) if match else 0

        # Check if conversion already in progress
        conversion_in_progress = "conversionProgressBar" in html

        return {
            "capture_points": capture_points,
            "base_time_seconds": PIRACY_BASE_CONVERSION_TIME,
            "time_per_crew": PIRACY_TIME_PER_CREW,
            "points_per_crew": PIRACY_POINTS_PER_CREW,
            "conversion_in_progress": conversion_in_progress
        }

    except Exception as e:
        print(f"Error fetching conversion data: {e}")
        traceback.print_exc()
        return None


def calculate_max_crew_conversion(attack_arrival_seconds, safety_buffer_seconds, conversion_data):
    """
    Calculate maximum crew points that can be converted before attack arrives.

    Parameters
    ----------
    attack_arrival_seconds : int
        Seconds until attack arrives
    safety_buffer_seconds : int
        Safety buffer (don't convert if attack arrives too close)
    conversion_data : dict
        Data from get_conversion_data()

    Returns
    -------
    max_crew : int
        Maximum crew points that can be converted in available time, or 0
    """
    available_time = attack_arrival_seconds - safety_buffer_seconds
    base_time = conversion_data.get("base_time_seconds", PIRACY_BASE_CONVERSION_TIME)
    time_per_crew = conversion_data.get("time_per_crew", PIRACY_TIME_PER_CREW)

    if available_time < base_time:
        return 0

    time_for_crew = available_time - base_time
    max_crew = int(time_for_crew / time_per_crew)
    return max(0, max_crew)


def convert_crew_for_defense(session, city, crew_points_to_convert):
    """
    Execute conversion and verify server response.

    Parameters
    ----------
    session : ikabot.web.session.Session
    city : dict
        City with pirate fortress
    crew_points_to_convert : int
        Number of crew points to convert

    Returns
    -------
    success : bool
    """
    try:
        data = {
            "action": "PiracyScreen",
            "function": "convert",
            "view": "pirateFortress",
            "cityId": city["id"],
            "islandId": city.get("islandId", 0),
            "activeTab": "tabCrew",
            "crewPoints": str(crew_points_to_convert),
            "position": str(city.get("fortress_pos", 17)),
            "backgroundView": "city",
            "currentCityId": city["id"],
            "templateView": "pirateFortress",
            "actionRequest": actionRequest,
            "ajax": "1",
        }

        resp = session.post(params=data, noIndex=True)

        # Check for error in response
        if resp and ('"type":3' in resp or '"type": "error"' in resp or "error" in resp.lower() and len(resp) < 200):
            print(f"Server rejected conversion: {resp}")
            return False

        return True

    except Exception as e:
        print(f"Error converting crew: {e}")
        traceback.print_exc()
        return False


def auto_defend_pirate_attack(session, target_city_id, attack_arrival_seconds,
                               max_capture_points=None, safety_buffer_seconds=10, allow_bonus_loss=False):
    """
    Automatically convert capture points to crew strength to defend against pirate attack.

    Parameters
    ----------
    session : ikabot.web.session.Session
    target_city_id : str or int
        City ID being attacked
    attack_arrival_seconds : int
        Seconds until attack arrives
    max_capture_points : int, optional
        Maximum capture points to spend (from user config), default unlimited
    safety_buffer_seconds : int
        Safety buffer in seconds (default 10)
    allow_bonus_loss : bool
        Allow spending below 7000 points (losing passive +1400 crew bonus), default False

    Returns
    -------
    result : dict
    """
    result = {
        "success": False,
        "reason": "",
        "crew_converted": 0,
        "capture_points_spent": 0,
        "conversion_time": 0,
        "attack_arrival_time": attack_arrival_seconds,
        "time_buffer": 0,
        "retry_later": False
    }

    try:
        start_eval_time = time.time()

        # 1. Find pirate fortress city (direct check of target city)
        fortress_city = get_pirate_fortress_city(session, target_city_id)
        if not fortress_city:
            result["reason"] = f"No pirate fortress found in city {target_city_id}"
            return result

        # 2. Get conversion status
        conversion_data = get_conversion_data(session, fortress_city)
        if not conversion_data:
            result["reason"] = "Failed to fetch conversion data from pirate fortress"
            result["retry_later"] = True
            return result

        # 3. Check if conversion already in progress
        if conversion_data["conversion_in_progress"]:
            result["reason"] = "Conversion already in progress"
            result["retry_later"] = True
            return result

        # Adjust remaining attack arrival seconds by elapsed I/O time
        elapsed = int(time.time() - start_eval_time)
        real_arrival_seconds = max(0, attack_arrival_seconds - elapsed)
        result["attack_arrival_time"] = real_arrival_seconds

        # 4. Check available capture points
        available_capture_points = conversion_data["capture_points"]
        points_per_crew = conversion_data["points_per_crew"]
        if available_capture_points < points_per_crew:
            result["reason"] = f"Not enough capture points (have {available_capture_points}, need {points_per_crew} min)"
            return result

        # 5. Calculate max crew based on time constraint
        max_crew_by_time = calculate_max_crew_conversion(
            real_arrival_seconds,
            safety_buffer_seconds,
            conversion_data
        )

        min_needed_time = conversion_data["base_time_seconds"] + safety_buffer_seconds
        if max_crew_by_time == 0:
            result["reason"] = f"Attack too close ({real_arrival_seconds}s) - need at least {min_needed_time}s"
            return result

        # 6. Apply 7000 CP threshold protection (+1400 crew bonus)
        # 7000 CP converted to crew = +700 crew, but loses +1400 bonus -> net LOSS of 700 crew!
        # If allow_bonus_loss is False, we preserve the 7000 CP threshold.
        if not allow_bonus_loss and available_capture_points >= PIRACY_BONUS_THRESHOLD:
            spendable_points = available_capture_points - PIRACY_BONUS_THRESHOLD
            if spendable_points < points_per_crew:
                result["success"] = True
                result["reason"] = "7,000 CP preserved to maintain maximum passive bonus (+1,400 crew strength)"
                result["crew_converted"] = 0
                return result
        else:
            spendable_points = available_capture_points

        # 7. Apply user spending limit if specified
        if max_capture_points:
            spendable_points = min(spendable_points, max_capture_points)

        max_crew_by_points = spendable_points // points_per_crew
        crew_to_convert = min(max_crew_by_time, max_crew_by_points)

        if crew_to_convert <= 0:
            result["reason"] = "Calculated 0 crew to convert (time/points/limit constraints)"
            return result

        # 8. Calculate actual conversion time and verify buffer
        conversion_time = conversion_data["base_time_seconds"] + (crew_to_convert * conversion_data["time_per_crew"])
        time_buffer = real_arrival_seconds - conversion_time

        if time_buffer < 0:
            result["reason"] = f"Conversion would take {conversion_time}s but attack arrives in {real_arrival_seconds}s"
            return result

        # 9. Perform conversion
        success = convert_crew_for_defense(session, fortress_city, crew_to_convert)

        if success:
            result["success"] = True
            result["crew_converted"] = crew_to_convert
            result["capture_points_spent"] = crew_to_convert * points_per_crew
            result["conversion_time"] = conversion_time
            result["time_buffer"] = time_buffer
        else:
            result["reason"] = "API call to convert crew was rejected by server"
            result["retry_later"] = True

        return result

    except Exception as e:
        result["reason"] = f"Exception: {str(e)}"
        traceback.print_exc()
        result["retry_later"] = True
        return result


def format_defense_result(result):
    """
    Format defense result for display in alerts.

    Parameters
    ----------
    result : dict
        Result from auto_defend_pirate_attack()

    Returns
    -------
    message : str
        Formatted message for user
    """
    if result["success"]:
        msg = "\n--- AUTO-DEFENSE ACTIVATED ---\n"
        if result["crew_converted"] > 0:
            msg += f"Converted: {result['crew_converted']} crew points\n"
            msg += f"Spent: {result['capture_points_spent']} capture points\n"
            msg += f"Conversion completes in: {daysHoursMinutes(result['conversion_time'])}\n"
            msg += f"Attack arrives in: {daysHoursMinutes(result['attack_arrival_time'])}\n"
            msg += f"Safety margin: {daysHoursMinutes(result['time_buffer'])}\n"
        else:
            msg += f"Status: {result['reason']}\n"
    else:
        msg = "\n--- AUTO-DEFENSE STATUS ---\n"
        msg += f"Notice: {result['reason']}\n"

    return msg
