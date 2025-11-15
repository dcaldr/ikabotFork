#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Emergency Pirate Defense - Manual Mode

User-callable command to manually trigger pirate defense when they see an incoming attack.

Flow:
1. Fetch current military movements
2. Show incoming pirate attacks to user
3. User selects attack (NO confirmation - time critical!)
4. Immediately convert crew for defense
5. Show result

This module can be called from menu (option 12.3) or used by alertAttacks for automatic mode.
"""

import sys
import re
import json

from ikabot.config import *
from ikabot.helpers.botComm import *
from ikabot.helpers.gui import *
from ikabot.helpers.pedirInfo import *
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.varios import daysHoursMinutes
from ikabot.helpers.pirateDefense import auto_defend_pirate_attack, format_defense_result


def emergencyDefense(session, event, stdin_fd, predetermined_input):
    """
    Manual emergency pirate defense command.

    Callable from menu. Scans for incoming pirate attacks and allows user
    to immediately convert crew for defense.

    Parameters
    ----------
    session : ikabot.web.session.Session
    event : multiprocessing.Event
    stdin_fd: int
    predetermined_input : multiprocessing.managers.SyncManager.list
    """
    sys.stdin = os.fdopen(stdin_fd)
    config.predetermined_input = predetermined_input

    try:
        banner()
        print("=== EMERGENCY PIRATE DEFENSE ===\n")
        print("Scanning for incoming pirate attacks...\n")

        # Fetch military movements
        html = session.get()
        city_id = re.search(r"currentCityId:\s(\d+),", html).group(1)
        url = f"view=militaryAdvisor&oldView=city&oldBackgroundView=city&backgroundView=city&currentCityId={city_id}&actionRequest={actionRequest}&ajax=1"
        movements_response = session.post(url)
        postdata = json.loads(movements_response, strict=False)
        militaryMovements = postdata[1][1][2]["viewScriptParams"]["militaryAndFleetMovements"]
        timeNow = int(postdata[0][1]["time"])

        # Filter for incoming pirate attacks
        pirate_attacks = []
        for movement in militaryMovements:
            if movement.get("isHostile") and not movement.get("isOwnArmyOrFleet"):
                # Check if it's a pirate attack
                is_pirate = (
                    movement["event"].get("type") == "piracy" and
                    movement["event"].get("missionIconClass") == "piracyRaid"
                )
                if is_pirate:
                    time_left = int(movement["eventTime"]) - timeNow
                    pirate_attacks.append({
                        "movement": movement,
                        "time_left": time_left,
                        "event_id": movement["event"]["id"]
                    })

        if not pirate_attacks:
            print("✓ No incoming pirate attacks detected.\n")
            print("Your cities are safe (for now)!")
            enter()
            event.set()
            return

        # Display pirate attacks
        print(f"Found {len(pirate_attacks)} incoming pirate attack(s):\n")
        for i, attack in enumerate(pirate_attacks, 1):
            mov = attack["movement"]
            origin = mov["origin"]
            target = mov["target"]
            time_str = daysHoursMinutes(attack["time_left"])

            print(f"({i}) {mov['event']['missionText']}")
            print(f"    From: {origin['name']} ({origin['avatarName']})")
            print(f"    To: {target['name']}")
            print(f"    Arrives in: {time_str} ({attack['time_left']} seconds)")
            print()

        # Get user configuration for spending limit
        session_data = session.getSessionData()
        defense_config = session_data.get("auto_pirate_defense", {})
        max_capture_points = defense_config.get("max_capture_points")
        safety_buffer = defense_config.get("safety_buffer_seconds", 120)

        if max_capture_points:
            print(f"Spending limit: {max_capture_points} capture points")
        else:
            print("Spending limit: Unlimited (use as many points as needed)")
        print(f"Safety buffer: {safety_buffer} seconds\n")

        # User selection - NO CONFIRMATION (time critical!)
        print("Select attack to defend against (0 to cancel):")
        choice = read(min=0, max=len(pirate_attacks), digit=True)

        if choice == 0:
            print("Canceled.")
            event.set()
            return

        # Get selected attack
        selected = pirate_attacks[choice - 1]
        target_city_id = selected["movement"]["target"]["cityId"]
        time_left = selected["time_left"]

        print(f"\nDefending against attack arriving in {daysHoursMinutes(time_left)}...")
        print("Converting crew... (NO CONFIRMATION - TIME CRITICAL!)\n")

        # Execute defense
        result = auto_defend_pirate_attack(
            session=session,
            target_city_id=target_city_id,
            attack_arrival_seconds=time_left,
            max_capture_points=max_capture_points,
            safety_buffer_seconds=safety_buffer
        )

        # Display result
        print(format_defense_result(result))

        if result["success"]:
            print("✓ Defense activated successfully!")
            print(f"  Crew conversion will complete {result['time_buffer']} seconds before attack.")
        else:
            print("✗ Defense failed!")
            print(f"  {result['reason']}")

        print("\nPress Enter to continue...")
        enter()

    except KeyboardInterrupt:
        event.set()
        return
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        enter()

    event.set()


def auto_defend_on_detection(session, pirate_attack_data):
    """
    Automatic defense trigger - called by alertAttacks when pirate detected.

    This is the shared function used by BOTH manual and automatic modes.

    Parameters
    ----------
    session : ikabot.web.session.Session
    pirate_attack_data : dict
        {
            "target_city_id": str,
            "time_left": int (seconds),
            "origin_name": str,
            "target_name": str
        }

    Returns
    -------
    result : dict
        Result from auto_defend_pirate_attack()
    """
    # Get user configuration
    session_data = session.getSessionData()
    defense_config = session_data.get("auto_pirate_defense", {})

    if not defense_config.get("enabled", False):
        return {
            "success": False,
            "reason": "Auto-defense not enabled in configuration"
        }

    max_capture_points = defense_config.get("max_capture_points")
    safety_buffer = defense_config.get("safety_buffer_seconds", 120)

    # Execute defense
    result = auto_defend_pirate_attack(
        session=session,
        target_city_id=pirate_attack_data["target_city_id"],
        attack_arrival_seconds=pirate_attack_data["time_left"],
        max_capture_points=max_capture_points,
        safety_buffer_seconds=safety_buffer
    )

    return result
