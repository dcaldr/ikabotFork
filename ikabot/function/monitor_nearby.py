#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import traceback
from ikabot.config import *
from ikabot.helpers.botComm import *
from ikabot.helpers.gui import *
from ikabot.helpers.pedirInfo import getIdsOfCities
from ikabot.helpers.process import set_child_mode
from ikabot.helpers.signals import setInfoSignal
from ikabot.helpers.varios import wait

def monitor_nearby(session, event, stdin_fd, predetermined_input):
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
        banner()
        print("Scans the area around your cities every X minutes.")
        interval_min = read(msg="Scan interval in minutes (default 60): ", min=1, default=60)
        
        print(f"I will scan the area around your cities every {interval_min} minutes.")
        enter()
    except KeyboardInterrupt:
        event.set()
        return

    set_child_mode(session)
    event.set()

    info = f"\nScanning nearby islands every {interval_min} minutes\n"
    setInfoSignal(session, info)
    try:
        do_it(session, interval_min)
    except Exception as e:
        msg = f"Error in:\n{info}\nCause:\n{traceback.format_exc()}"
        sendToBot(session, msg)
    finally:
        session.logout()

def do_it(session, interval_min):
    """
    Parameters
    ----------
    session : ikabot.web.session.Session
    interval_min : int
    """
    while True:
        try:
            # Get all user cities
            ids, cities = getIdsOfCities(session)
            
            # Collect unique scanning coordinates
            # We want key islands around each city. Radius 2 means:
            # City at (x,y). Scan (x-2, y-2) to (x+2, y+2).
            # But getJSONArea takes x_min, x_max, y_min, y_max.
            # We can just iterate through cities and request the area.
            # To avoid duplicate requests if cities are close, we could track 'seen' areas?
            # Simpler: Just request for each city. The game handles it (or we cache).
            # Given we sleep 60 mins, duplicate requests aren't a huge deal, but let's be polite.
            
            # Map areas to scan: (x_min, x_max, y_min, y_max)
            areas = []
            for city_id in cities:
                html = session.get(city_url + city_id)
                city = getCity(html)
                cx = int(city['x'])
                cy = int(city['y'])
                
                # Radius 2
                areas.append((max(0, cx - 2), min(100, cx + 2), max(0, cy - 2), min(100, cy + 2)))

            # Execute scans
            for x_min, x_max, y_min, y_max in areas:
                # API expects: action=WorldMap&function=getJSONArea&x_min=XX&x_max=XX&y_min=YY&y_max=YY
                url = f"action=WorldMap&function=getJSONArea&x_min={x_min}&x_max={x_max}&y_min={y_min}&y_max={y_max}"
                data = session.post(url)
                
                # The getJSONArea returns shallow data. 
                # To actually "update" the specific island details in Ikabot's internal DB (if it keeps one?), 
                # we usually need to visit the island view.
                # Ikabot caches island data in .ikabot file when getIsland is called.
                # getJSONArea returns IDs. We should explicitly visit them to ensure full data update.
                
                island_data = json.loads(data)
                if 'data' in island_data:
                    for x_str, x_val in island_data['data'].items():
                        for y_str, island_info in x_val.items():
                            # island_info: [id, name, resource, miracle, ?, ?, wood_lvl, players, ...]
                            island_id = island_info[0]
                            if int(island_id) > 0: # Valid island
                                try:
                                    session.get(f"view=island&islandId={island_id}")
                                except Exception:
                                    pass # Ignore connection glitches
                                time.sleep(0.5) # Polite delay between island views

        except Exception as e:
            # Log but don't crash loop
            sendToBot(session, f"Error in monitor_nearby loop: {e}")

        # Sleep
        time.sleep(interval_min * 60)

def getCity(html):
    """
    Helper to extract city coords if not readily available in 'cities' dict.
    (Usually getIdsOfCities returns dict of cities, but checking content to be safe)
    """
    # The 'cities' dict from getIdsOfCities contains city objects captured from the dropdown or similar.
    # It usually has 'x' and 'y'.
    # If not, we parse it.
    # But wait, getIdsOfCities logic:
    # ids = [id1, id2...]
    # cities = {id1: cityData1, ...}
    # cityData often comes from generic implementation.
    # Let's trust the logic inside do_it loop using getCity(html) for freshness.
    
    # Simple regex for coords in city view
    # "coords":{[1,1]} or similar?
    # Or breadcrumbs?
    # Let's rely on standard 'ikabot.helpers.getJson.getCity' if available, but I didn't import it.
    # I imported 'getCity' from 'ikabot.helpers.getJson' in previous files.
    # Let's add the import.
    from ikabot.helpers.getJson import getCity as getCityHelper
    return getCityHelper(html)

