#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helper module for automatic pirate defense via crew conversion.

When a pirate attack is detected, this module:
1. Fetches current capture points available
2. Calculates max crew points that can be converted in time
3. Converts capture points to crew strength BEFORE attack arrives
4. Returns result for alerting user

Critical timing constraint: Conversion MUST complete before attack arrives.
"""

import re
import json
import traceback

from ikabot.config import actionRequest
from ikabot.helpers.getJson import getIdsOfCities, getCity
from ikabot.helpers.varios import daysHoursMinutes


def get_pirate_fortress_city(session):
    """
    Find a city with a pirate fortress.

    Parameters
    ----------
    session : ikabot.web.session.Session

    Returns
    -------
    city : dict or None
        City dict with pirate fortress, or None if no fortress found
    """
    try:
        city_ids = getIdsOfCities(session)[0]
        for city_id in city_ids:
            html = session.get(f"?view=city&cityId={city_id}")
            city = getCity(html)

            # Check for pirate fortress in city positions
            for pos, building in enumerate(city["position"]):
                if building.get("building") == "pirateFortress":
                    city["fortress_pos"] = pos
                    city["fortress_level"] = building.get("level", 0)
                    return city

        return None
    except Exception as e:
        print(f"Error finding pirate fortress: {e}")
        return None


def get_conversion_data(session, city):
    """
    Fetch pirate fortress conversion data dynamically from API.

    Parses the pirate fortress crew conversion screen to get:
    - Current capture points available
    - Base conversion time (startup penalty)
    - Time per crew point
    - Capture points per crew point
    - Whether conversion is already in progress

    Parameters
    ----------
    session : ikabot.web.session.Session
    city : dict
        City with pirate fortress

    Returns
    -------
    data : dict
        {
            "capture_points": int,
            "base_time_seconds": int,  # e.g., 156
            "time_per_crew": int,      # e.g., 7
            "points_per_crew": int,    # e.g., 10
            "conversion_in_progress": bool
        }
    or None if error
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
        match = re.search(r'\\"capturePoints\\":\\"(\d+)\\"', html)
        if not match:
            match = re.search(r'"capturePoints":"(\d+)"', html)
        capture_points = int(match.group(1)) if match else 0

        # Check if conversion already in progress
        conversion_in_progress = "conversionProgressBar" in html

        # Extract conversion costs from HTML
        # Look for: <li class="capturePoints"><span class="value">10</span>
        points_match = re.search(r'class="capturePoints"[^>]*>.*?<span class="value">(\d+)</span>', html, re.DOTALL)
        points_per_crew = int(points_match.group(1)) if points_match else 10

        # Look for: <li class="time"><span class="value">7s</span>
        time_match = re.search(r'class="time"[^>]*>.*?<span class="value">(\d+)s</span>', html, re.DOTALL)
        time_per_crew = int(time_match.group(1)) if time_match else 7

        # Look for base time: "Pro přeměnu je základní doba 2m 36s"
        base_time_match = re.search(r'základní doba (\d+)m\s*(\d+)s', html)
        if base_time_match:
            minutes = int(base_time_match.group(1))
            seconds = int(base_time_match.group(2))
            base_time_seconds = minutes * 60 + seconds
        else:
            # Fallback: try English version or default
            base_time_match = re.search(r'base time (\d+)m\s*(\d+)s', html, re.IGNORECASE)
            if base_time_match:
                minutes = int(base_time_match.group(1))
                seconds = int(base_time_match.group(2))
                base_time_seconds = minutes * 60 + seconds
            else:
                base_time_seconds = 156  # Default fallback

        return {
            "capture_points": capture_points,
            "base_time_seconds": base_time_seconds,
            "time_per_crew": time_per_crew,
            "points_per_crew": points_per_crew,
            "conversion_in_progress": conversion_in_progress
        }

    except Exception as e:
        print(f"Error fetching conversion data: {e}")
        traceback.print_exc()
        return None


def calculate_max_crew_conversion(attack_arrival_seconds, safety_buffer_seconds, conversion_data):
    """
    Calculate maximum crew points that can be converted before attack arrives.

    Formula:
        available_time = attack_arrival - safety_buffer
        if available_time < base_time: return 0 (not enough time)
        max_crew = (available_time - base_time) / time_per_crew

    Parameters
    ----------
    attack_arrival_seconds : int
        Seconds until attack arrives
    safety_buffer_seconds : int
        Safety buffer (don't convert if attack too close)
    conversion_data : dict
        Data from get_conversion_data()

    Returns
    -------
    max_crew : int
        Maximum crew points that can be converted, or 0 if not enough time
    """
    available_time = attack_arrival_seconds - safety_buffer_seconds
    base_time = conversion_data["base_time_seconds"]
    time_per_crew = conversion_data["time_per_crew"]

    if available_time < base_time:
        return 0  # Not enough time even for base conversion

    # Calculate max crew points
    time_for_crew = available_time - base_time
    max_crew = int(time_for_crew / time_per_crew)

    return max(0, max_crew)


def convert_crew_for_defense(session, city, crew_points_to_convert):
    """
    Convert capture points to crew strength.

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
            "islandId": city["islandId"],
            "activeTab": "tabCrew",
            "crewPoints": str(crew_points_to_convert),
            "position": str(city.get("fortress_pos", 17)),
            "backgroundView": "city",
            "currentCityId": city["id"],
            "templateView": "pirateFortress",
            "actionRequest": actionRequest,
            "ajax": "1",
        }

        session.post(params=data, noIndex=True)
        return True

    except Exception as e:
        print(f"Error converting crew: {e}")
        traceback.print_exc()
        return False


def auto_defend_pirate_attack(session, target_city_id, attack_arrival_seconds,
                               max_capture_points=None, safety_buffer_seconds=10, allow_bonus_loss=False):
    """
    Automatically convert capture points to crew strength to defend against pirate attack.

    This is the main function called by both automatic and manual modes.

    Parameters
    ----------
    session : ikabot.web.session.Session
    target_city_id : str
        City ID being attacked
    attack_arrival_seconds : int
        Seconds until attack arrives
    max_capture_points : int, optional
        Maximum capture points to spend (from user config), default unlimited
    safety_buffer_seconds : int
        Safety buffer in seconds (default 10)
    allow_bonus_loss : bool
        Allow spending that drops below 7000 points (loses crew bonus), default False

    Returns
    -------
    result : dict
        {
            "success": bool,
            "reason": str (if failed),
            "crew_converted": int,
            "capture_points_spent": int,
            "conversion_time": int (seconds),
            "attack_arrival_time": int (seconds),
            "time_buffer": int (seconds margin before attack)
        }
    """
    result = {
        "success": False,
        "reason": "",
        "crew_converted": 0,
        "capture_points_spent": 0,
        "conversion_time": 0,
        "attack_arrival_time": attack_arrival_seconds,
        "time_buffer": 0
    }

    try:
        # 1. Find pirate fortress
        fortress_city = get_pirate_fortress_city(session)
        if not fortress_city:
            result["reason"] = "No pirate fortress found in any city"
            return result

        # 2. Get conversion data
        conversion_data = get_conversion_data(session, fortress_city)
        if not conversion_data:
            result["reason"] = "Failed to fetch conversion data from pirate fortress"
            return result

        # 3. Check if conversion already in progress
        if conversion_data["conversion_in_progress"]:
            result["reason"] = "Conversion already in progress, cannot start another"
            return result

        # 4. Check available capture points
        available_capture_points = conversion_data["capture_points"]
        if available_capture_points < conversion_data["points_per_crew"]:
            result["reason"] = f"Not enough capture points (have {available_capture_points}, need {conversion_data['points_per_crew']} minimum)"
            return result

        # 5. Calculate max crew based on time constraint
        max_crew_by_time = calculate_max_crew_conversion(
            attack_arrival_seconds,
            safety_buffer_seconds,
            conversion_data
        )

        if max_crew_by_time == 0:
            result["reason"] = f"Attack too close ({attack_arrival_seconds}s) - need at least {conversion_data['base_time_seconds'] + safety_buffer_seconds}s"
            return result

        # 6. Calculate max crew based on available capture points
        max_crew_by_points = available_capture_points // conversion_data["points_per_crew"]

        # 7. Apply user spending limit if specified
        if max_capture_points:
            max_crew_by_limit = max_capture_points // conversion_data["points_per_crew"]
            crew_to_convert = min(max_crew_by_time, max_crew_by_points, max_crew_by_limit)
        else:
            crew_to_convert = min(max_crew_by_time, max_crew_by_points)

        # 7b. Apply 7000 points bonus threshold protection if enabled
        if not allow_bonus_loss and available_capture_points >= 7000:
            # Calculate max crew that keeps us at exactly 7000 points (preserve bonus)
            max_spend_for_bonus = available_capture_points - 7000
            max_crew_by_bonus = max_spend_for_bonus // conversion_data["points_per_crew"]
            crew_to_convert = min(crew_to_convert, max_crew_by_bonus)

        if crew_to_convert == 0:
            result["reason"] = "Calculated 0 crew to convert (time/points/limit constraints)"
            return result

        # 8. Calculate actual conversion time
        conversion_time = conversion_data["base_time_seconds"] + (crew_to_convert * conversion_data["time_per_crew"])
        time_buffer = attack_arrival_seconds - conversion_time

        if time_buffer < 0:
            result["reason"] = f"Conversion would take {conversion_time}s but attack in {attack_arrival_seconds}s"
            return result

        # 9. Perform conversion
        success = convert_crew_for_defense(session, fortress_city, crew_to_convert)

        if success:
            result["success"] = True
            result["crew_converted"] = crew_to_convert
            result["capture_points_spent"] = crew_to_convert * conversion_data["points_per_crew"]
            result["conversion_time"] = conversion_time
            result["time_buffer"] = time_buffer
        else:
            result["reason"] = "API call to convert crew failed"

        return result

    except Exception as e:
        result["reason"] = f"Exception: {str(e)}"
        traceback.print_exc()
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
        msg += f"Converted: {result['crew_converted']} crew points\n"
        msg += f"Spent: {result['capture_points_spent']} capture points\n"
        msg += f"Conversion completes in: {daysHoursMinutes(result['conversion_time'])}\n"
        msg += f"Attack arrives in: {daysHoursMinutes(result['attack_arrival_time'])}\n"
        msg += f"Safety margin: {daysHoursMinutes(result['time_buffer'])}\n"
    else:
        msg = "\n--- AUTO-DEFENSE FAILED ---\n"
        msg += f"Reason: {result['reason']}\n"

    return msg
