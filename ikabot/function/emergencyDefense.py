#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Emergency Pirate Defense - Manual Mode & Configuration

User-callable command to:
1. Manually trigger pirate defense when they see an incoming attack
2. Configure auto-defense settings (used by alertAttacks)

Flow:
- Manual defense: Scan for attacks → user selects → immediately convert
- Configuration: Set up auto-defense preferences (max points, buffer, etc.)

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


def configure_auto_defense(session):
    """
    Configure auto-pirate defense settings.

    This function is called during emergencyDefense setup to configure
    automatic defense preferences. Can also be called standalone.

    Parameters
    ----------
    session : ikabot.web.session.Session
    """
    banner()
    print("=== Auto-Pirate Defense Configuration ===\n")
    print("Configure automatic crew conversion when pirate attacks are detected.")
    print("This works with the alertAttacks feature.\n")

    auto_defend = read(msg="Enable auto-defense? (y/N): ", values=["y", "Y", "n", "N", ""])

    if auto_defend.lower() == "y":
        print("\nMaximum CAPTURE POINTS to spend per attack?")
        print("(Leave empty for unlimited)")
        max_points_input = read(msg="Max capture points (default: unlimited): ", min=0, digit=True, empty=True)
        max_capture_points = int(max_points_input) if max_points_input != "" else None

        print("\nSafety buffer in SECONDS (won't convert if attack too close)?")
        print("Note: Conversion has ~156 second base time + 7 sec per crew point")
        safety_buffer = read(msg="Safety buffer (default: 120): ", min=0, digit=True, default=120)

        # Store configuration
        session_data = session.getSessionData()
        session_data["auto_pirate_defense"] = {
            "enabled": True,
            "max_capture_points": max_capture_points,
            "safety_buffer_seconds": safety_buffer
        }
        session.setSessionData(session_data)

        print("\n" + "="*50)
        if max_capture_points:
            print(f"✓ Auto-defense ENABLED")
            print(f"  Max capture points: {max_capture_points}")
            print(f"  Safety buffer: {safety_buffer} seconds")
        else:
            print(f"✓ Auto-defense ENABLED")
            print(f"  Max capture points: UNLIMITED")
            print(f"  Safety buffer: {safety_buffer} seconds")
        print("="*50)
    else:
        # Ensure disabled
        session_data = session.getSessionData()
        session_data["auto_pirate_defense"] = {"enabled": False}
        session.setSessionData(session_data)
        print("\n✓ Auto-defense DISABLED")

    print("\nPress Enter to continue...")
    enter()


def emergencyDefense(session, event, stdin_fd, predetermined_input):
    """
    Manual emergency pirate defense command with configuration option.

    Callable from menu. User can:
    1. Configure auto-defense settings
    2. Manually scan and defend against current pirate attacks

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
        print("(1) Defend against current pirate attacks (manual)")
        print("(2) Configure auto-defense settings")
        print("(0) Back\n")

        choice = read(min=0, max=2, digit=True)

        if choice == 0:
            event.set()
            return
        elif choice == 2:
            configure_auto_defense(session)
            event.set()
            return

        # Continue with manual defense (choice == 1)
        banner()
        print("=== MANUAL PIRATE DEFENSE ===\n")
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
