#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import time
import traceback
# DEBUG LOGGING: Added imports for comprehensive attack data logging
import json
import os
from pathlib import Path

from ikabot.function.vacationMode import activateVacationMode
from ikabot.function.emergencyDefense import auto_defend_on_detection
from ikabot.helpers.botComm import *
from ikabot.helpers.gui import enter
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.signals import setInfoSignal
from ikabot.helpers.varios import daysHoursMinutes
from ikabot.helpers.pirateDefense import format_defense_result


# DEBUG LOGGING: Comprehensive logging function to discover API structure for attack classification
def log_attack_debug(militaryMovement, all_movements, postdata, session, current_city_id, time_now, time_left):
    """
    Log EVERYTHING related to attack detection for debugging and API structure discovery.

    This function captures comprehensive data to help identify how to distinguish:
    - Pirate attacks vs player attacks
    - Different attack types (raid, pillage, occupy, etc.)
    - Own movements vs incoming movements
    - Any other attack classifications available in the API

    Captures:
    - The specific hostile movement that triggered the alert
    - ALL military movements (to compare hostile vs non-hostile, own vs incoming)
    - Full API response (postdata) - the complete raw data from Ikariam server
    - Session info (server, world, player) - context for the data
    - Current city context - which city we're viewing from
    - Statistics - counts of different movement types
    - Precise timing data (server time, event time, time left in seconds)

    Creates/appends to ~/.ikabot/alert_debug.log with JSON data (one entry per line)

    Parameters
    ----------
    militaryMovement : dict
        The hostile movement object that triggered this alert
    all_movements : list[dict]
        Complete list of ALL military movements from API (hostile and non-hostile)
    postdata : dict/list
        Full raw API response from militaryAdvisor endpoint
    session : ikabot.web.session.Session
        Current session with server/world/player info
    current_city_id : str
        ID of the city we're currently viewing from
    time_now : int
        Server's current timestamp (from API response)
    time_left : int
        Calculated seconds until attack arrival (eventTime - timeNow)
    """
    try:
        # DEBUG LOGGING: Create log directory if it doesn't exist
        log_dir = Path.home() / "ikalog"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "alert_debug.log"

        # DEBUG LOGGING: Prepare comprehensive log entry with EVERYTHING
        log_entry = {
            # Timestamp information
            "timestamp": time.time(),
            "timestamp_readable": time.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),

            # Session context - who/where/when
            "session": {
                "server": session.servidor if hasattr(session, 'servidor') else None,
                "world": session.mundo if hasattr(session, 'mundo') else None,
                "player": session.username if hasattr(session, 'username') else None,
                "current_city_id": current_city_id,
                "pid": os.getpid()
            },

            # The hostile movement that triggered this alert
            "triggered_movement": militaryMovement,

            # ALL military movements (for comparison and pattern discovery)
            "all_movements": all_movements,

            # Count statistics to understand movement distribution
            "stats": {
                "total_movements": len(all_movements),
                "hostile_movements": len([m for m in all_movements if m.get("isHostile")]),
                "own_movements": len([m for m in all_movements if m.get("isOwnArmyOrFleet")]),
                "incoming_movements": len([m for m in all_movements
                                          if m.get("isHostile") and not m.get("isOwnArmyOrFleet")]),
                "outgoing_own_hostile": len([m for m in all_movements
                                            if m.get("isHostile") and m.get("isOwnArmyOrFleet")])
            },

            # Full API response - EVERYTHING the server sent us
            "raw_api_response": postdata,

            # Extracted data from triggered movement for quick reference
            "quick_ref": {
                "event_id": militaryMovement.get("event", {}).get("id"),
                "mission_text": militaryMovement.get("event", {}).get("missionText"),
                "origin_name": militaryMovement.get("origin", {}).get("name"),
                "origin_avatar": militaryMovement.get("origin", {}).get("avatarName"),
                "origin_avatar_id": militaryMovement.get("origin", {}).get("avatarId"),
                "origin_type": militaryMovement.get("origin", {}).get("type"),
                "origin_city_id": militaryMovement.get("origin", {}).get("cityId"),
                "origin_island_id": militaryMovement.get("origin", {}).get("islandId"),
                "target_name": militaryMovement.get("target", {}).get("name"),
                "target_id": militaryMovement.get("target", {}).get("id"),
                "target_avatar_id": militaryMovement.get("target", {}).get("avatarId"),
                "target_city_id": militaryMovement.get("target", {}).get("cityId"),
                "target_island_id": militaryMovement.get("target", {}).get("islandId"),
                "army_amount": militaryMovement.get("army", {}).get("amount"),
                "fleet_amount": militaryMovement.get("fleet", {}).get("amount"),
                "is_hostile": militaryMovement.get("isHostile"),
                "is_own": militaryMovement.get("isOwnArmyOrFleet"),
                "is_same_alliance": militaryMovement.get("isSameAlliance"),
                "hide_units": militaryMovement.get("hideUnits"),  # CRITICAL: True for piracy
                "event_time": militaryMovement.get("eventTime"),
                "event_type": militaryMovement.get("event", {}).get("type"),  # CRITICAL: "piracy" for pirate attacks
                "event_mission": militaryMovement.get("event", {}).get("mission"),  # Mission ID number
                "event_mission_icon": militaryMovement.get("event", {}).get("missionIconClass"),  # CRITICAL: "piracyRaid" for pirates
                "event_mission_state": militaryMovement.get("event", {}).get("missionState"),
                "mission_type": militaryMovement.get("event", {}).get("missionType")
            },

            # Classification hints for pirate detection
            "pirate_indicators": {
                "is_piracy_type": militaryMovement.get("event", {}).get("type") == "piracy",
                "is_piracy_icon": militaryMovement.get("event", {}).get("missionIconClass") == "piracyRaid",
                "units_hidden": militaryMovement.get("hideUnits") == True,
                "likely_pirate": (
                    militaryMovement.get("event", {}).get("type") == "piracy" and
                    militaryMovement.get("event", {}).get("missionIconClass") == "piracyRaid"
                )
            },

            # Precise timing data (all in seconds, Unix timestamps)
            "timing": {
                "server_time_now": time_now,                    # Server's current time (Unix timestamp)
                "attack_event_time": militaryMovement.get("eventTime"),  # Attack arrival time (Unix timestamp)
                "time_left_seconds": time_left,                 # Exact seconds until arrival
                "time_left_formatted": daysHoursMinutes(time_left)  # Human-readable format (e.g., "1H 23M")
            },

            # All available keys in the triggered movement (for discovery)
            "available_keys": {
                "top_level": list(militaryMovement.keys()),
                "event": list(militaryMovement.get("event", {}).keys()) if isinstance(militaryMovement.get("event"), dict) else [],
                "origin": list(militaryMovement.get("origin", {}).keys()) if isinstance(militaryMovement.get("origin"), dict) else [],
                "target": list(militaryMovement.get("target", {}).keys()) if isinstance(militaryMovement.get("target"), dict) else [],
                "army": list(militaryMovement.get("army", {}).keys()) if isinstance(militaryMovement.get("army"), dict) else [],
                "fleet": list(militaryMovement.get("fleet", {}).keys()) if isinstance(militaryMovement.get("fleet"), dict) else []
            }
        }

        # DEBUG LOGGING: Append to log file in JSON Lines format (one JSON object per line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + "\n")

        # DEBUG LOGGING: Log summary to console for immediate feedback
        summary = (
            f"[DEBUG] Attack logged: '{log_entry['quick_ref']['mission_text']}' "
            f"from {log_entry['quick_ref']['origin_avatar']} "
            f"(hostile={log_entry['quick_ref']['is_hostile']}, "
            f"own={log_entry['quick_ref']['is_own']}) "
            f"-> {log_file}"
        )
        print(summary)

    except Exception as e:
        # DEBUG LOGGING: Don't crash alertAttacks if logging fails
        print(f"[DEBUG] Alert logging failed: {e}")
        traceback.print_exc()


def alertAttacks(session, event, stdin_fd, predetermined_input):
    """
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
        if checkTelegramData(session) is False:
            event.set()
            return

        banner()
        default = 20
        minutes = read(
            msg=
                "How often should I search for attacks?(min:3, default: {:d}): ".format(default),
            min=3,
            default=default,
        )
        # min_units = read(msg=_('Attacks with less than how many units should be ignored? (default: 0): '), digit=True, default=0)
        print("I will check for attacks every {:d} minutes".format(minutes))
        print("\nTIP: To enable auto-pirate defense, use menu option 12.3 (Emergency Pirate Defense → Configure)")
        enter()
    except KeyboardInterrupt:
        event.set()
        return

    set_child_mode(session)
    event.set()

    info = "\nI check for attacks every {:d} minutes\n".format(minutes)
    setInfoSignal(session, info)
    try:
        do_it(session, minutes)
    except Exception as e:
        msg = "Error in:\n{}\nCause:\n{}".format(info, traceback.format_exc())
        sendToBot(session, msg)
    finally:
        session.logout()


def respondToAttack(session):
    """
    Parameters
    ---------
    session : ikabot.web.session.Session
    """

    # this allows the user to respond to an attack via telegram
    while True:
        time.sleep(60 * 3)
        responses = getUserResponse(session)
        for response in responses:
            # the response should be in the form of:
            # <pid>:<action number>
            rta = re.search(r"(\d+):?\s*(\d+)", response)
            if rta is None:
                continue

            pid = int(rta.group(1))
            action = int(rta.group(2))

            # if the pid doesn't match, we ignore it
            if pid != os.getpid():
                continue

            # currently just one action is supported
            if action == 1:
                # mv
                activateVacationMode(session)
            else:
                sendToBot(session, "Invalid command: {:d}".format(action))


def do_it(session, minutes):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    minutes : int
    """

    # this thread lets the user react to an attack once the alert is sent
    thread = threading.Thread(target=respondToAttack, args=(session,))
    thread.start()

    knownAttacks = []
    while True:
        ##Catch errors inside the function to not exit for any reason.
        currentAttacks = []
        try:
            # get the militaryMovements
            html = session.get()
            city_id = re.search(r"currentCityId:\s(\d+),", html).group(1)
            url = "view=militaryAdvisor&oldView=city&oldBackgroundView=city&backgroundView=city&currentCityId={}&actionRequest={}&ajax=1".format(
                city_id, actionRequest
            )
            movements_response = session.post(url)
            postdata = json.loads(movements_response, strict=False)
            militaryMovements = postdata[1][1][2]["viewScriptParams"][
                "militaryAndFleetMovements"
            ]
            timeNow = int(postdata[0][1]["time"])

            for militaryMovement in [
                mov for mov in militaryMovements if mov["isHostile"]
            ]:
                event_id = militaryMovement["event"]["id"]
                currentAttacks.append(event_id)
                # if we already alerted this, do nothing
                if event_id not in knownAttacks:
                    knownAttacks.append(event_id)

                    # get information about the attack
                    missionText = militaryMovement["event"]["missionText"]
                    origin = militaryMovement["origin"]
                    target = militaryMovement["target"]
                    amountTroops = militaryMovement["army"]["amount"]
                    amountFleets = militaryMovement["fleet"]["amount"]
                    timeLeft = int(militaryMovement["eventTime"]) - timeNow

                    # DEBUG LOGGING: Only log INCOMING attacks (not own outgoing pirate missions)
                    # Filter: isHostile=true AND isOwnArmyOrFleet=false
                    # This captures: triggered movement, all movements, full API response, session context, statistics, precise timing
                    # Log file location: ~/.ikabot/alert_debug.log (JSON Lines format)
                    
                    log_attack_debug(
                        militaryMovement=militaryMovement,     # The hostile movement that triggered alert
                        all_movements=militaryMovements,       # ALL movements (to compare patterns)
                        postdata=postdata,                     # Full raw API response
                        session=session,                       # Session with server/world/player info
                        current_city_id=city_id,               # Current city context
                        time_now=timeNow,                      # Server's current time (Unix timestamp)
                        time_left=timeLeft                     # Seconds until attack arrival
                    )

                    # Classify attack type: pirate vs normal player attack
                    isPirate = (
                        militaryMovement["event"].get("type") == "piracy" and
                        militaryMovement["event"].get("missionIconClass") == "piracyRaid"
                    )

                    # send alert
                    if isPirate:
                        msg = "-- PIRATE ATTACK --\n"
                        msg += missionText + "\n"
                        msg += "from the pirate fortress {} of {}\n".format(
                            origin["name"], origin["avatarName"]
                        )
                        msg += "to {}\n".format(target["name"])
                        msg += "arrival in: {}\n".format(daysHoursMinutes(timeLeft))
                        msg += "(Pirate attacks cannot show unit/fleet numbers)\n"

                        # Auto-defend against pirate attack if enabled
                        try:
                            pirate_attack_data = {
                                "target_city_id": target["cityId"],
                                "time_left": timeLeft,
                                "origin_name": origin["name"],
                                "target_name": target["name"]
                            }
                            defense_result = auto_defend_on_detection(session, pirate_attack_data)
                            msg += format_defense_result(defense_result)
                        except Exception as e:
                            msg += f"\n--- AUTO-DEFENSE ERROR ---\n{str(e)}\n"

                    else:
                        msg = "-- ALERT --\n"
                        msg += missionText + "\n"
                        msg += "from the city {} of {}\n".format(
                            origin["name"], origin["avatarName"]
                        )
                        msg += "a {}\n".format(target["name"])
                        msg += "{} units\n".format(amountTroops)
                        msg += "{} fleet\n".format(amountFleets)
                        msg += "arrival in: {}\n".format(daysHoursMinutes(timeLeft))
                        msg += "If you want to put the account in vacation mode send:\n"
                        msg += "{:d}:1".format(os.getpid())

                    sendToBot(session, msg)

        except Exception as e:
            info = "\nI check for attacks every {:d} minutes\n".format(minutes)
            msg = "Error in:\n{}\nCause:\n{}".format(info, traceback.format_exc())
            sendToBot(session, msg)

        # remove old attacks from knownAttacks
        for event_id in list(knownAttacks):
            if event_id not in currentAttacks:
                knownAttacks.remove(event_id)

        time.sleep(minutes * 60)
