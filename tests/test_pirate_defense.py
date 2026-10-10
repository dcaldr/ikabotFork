#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
import json
from pathlib import Path

from ikabot.helpers.pirateDefense import (
    calculate_max_crew_conversion,
    auto_defend_pirate_attack,
    PIRACY_POINTS_PER_CREW,
    PIRACY_TIME_PER_CREW,
    PIRACY_BASE_CONVERSION_TIME,
    PIRACY_BONUS_THRESHOLD,
    PIRACY_BONUS_CREW
)


class DummySession:
    """Mock session for testing pirate defense logic."""
    def __init__(self, username="pooky756", fortress_city_id="1000", capture_points=10000, in_progress=False, reject_post=False):
        self.username = username
        self.fortress_city_id = str(fortress_city_id)
        self.capture_points = capture_points
        self.in_progress = in_progress
        self.reject_post = reject_post
        self.post_called = False
        self.post_data = {}
        self._session_data = {"pirate_fortress_city_id": self.fortress_city_id}

    def getSessionData(self):
        return self._session_data

    def setSessionData(self, data):
        self._session_data = data

    def get(self, url=""):
        city_json = {
            "id": self.fortress_city_id,
            "ownerId": "100537",
            "ownerName": self.username,
            "name": "Pentelikon",
            "islandXCoord": 6,
            "islandYCoord": 6,
            "islandId": 5461,
            "position": [
                {"building": "townHall", "level": 10},
                {"building": "pirateFortress", "level": 15}
            ]
        }
        return f'[["updateBackgroundData", {json.dumps(city_json)}],["updateTemplateData", ""]]'

    def post(self, params=None, noIndex=False):
        self.post_called = True
        self.post_data = params or {}
        if self.reject_post:
            return '{"type": 3, "error": "Action rejected"}'
        progress = "conversionProgressBar" if self.in_progress else ""
        return f'{{"capturePoints": "{self.capture_points}"}} {progress}'


class TestPirateDefense(unittest.TestCase):

    def test_calculate_max_crew_conversion_time_bounds(self):
        conversion_data = {
            "base_time_seconds": 156,
            "time_per_crew": 7
        }
        # If available time < 156s + 10s buffer -> 0
        self.assertEqual(calculate_max_crew_conversion(160, 10, conversion_data), 0)
        # If arrival is 300s, buffer 10s -> available = 290s.
        # (290 - 156) // 7 = 134 // 7 = 19 crew points
        self.assertEqual(calculate_max_crew_conversion(300, 10, conversion_data), 19)

    def test_bonus_protection_keeps_7000_threshold(self):
        # Account has 10,000 CP. With protection, only 3,000 CP is spendable (300 crew)
        session = DummySession(capture_points=10000)
        # Give enough time: 3600 seconds
        result = auto_defend_pirate_attack(
            session=session,
            target_city_id="1000",
            attack_arrival_seconds=3600,
            safety_buffer_seconds=10,
            allow_bonus_loss=False
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["crew_converted"], 300)
        self.assertEqual(result["capture_points_spent"], 3000)

    def test_bonus_protection_at_exactly_7000(self):
        # Account has exactly 7,000 CP. Should NOT fail, but report preservation of +1400 bonus
        session = DummySession(capture_points=7000)
        result = auto_defend_pirate_attack(
            session=session,
            target_city_id="1000",
            attack_arrival_seconds=3600,
            safety_buffer_seconds=10,
            allow_bonus_loss=False
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["crew_converted"], 0)
        self.assertIn("7,000 CP preserved", result["reason"])

    def test_allow_bonus_loss_spends_under_7000(self):
        # Account has 5,000 CP (already below threshold or user allows loss)
        # 500 crew requires: 156 + 500 * 7 = 3656s + 10s buffer = 3666s. Set arrival to 4000s
        session = DummySession(capture_points=5000)
        result = auto_defend_pirate_attack(
            session=session,
            target_city_id="1000",
            attack_arrival_seconds=4000,
            safety_buffer_seconds=10,
            allow_bonus_loss=True
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["crew_converted"], 500)
        self.assertEqual(result["capture_points_spent"], 5000)

    def test_conversion_in_progress_triggers_retry_later(self):
        session = DummySession(capture_points=10000, in_progress=True)
        result = auto_defend_pirate_attack(
            session=session,
            target_city_id="1000",
            attack_arrival_seconds=1800
        )
        self.assertFalse(result["success"])
        self.assertTrue(result.get("retry_later"))
        self.assertIn("in progress", result["reason"])

    def test_fixture_real_raid_detection(self):
        fixture_path = Path("tests/fixtures/czech_server/alert_debug.log")
        if not fixture_path.exists():
            return

        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.loads(f.readline())

        all_movements = data["all_movements"]
        my_city_ids = ["1000", "912", "1101"]  # Cities of player pooky756
        username = "pooky756"

        filtered_attacks = []
        for mov in all_movements:
            if not mov.get("isHostile"):
                continue
            origin = mov.get("origin", {})
            target = mov.get("target", {})
            if origin.get("avatarName") == username:
                continue
            if str(target.get("cityId")) not in my_city_ids:
                continue
            filtered_attacks.append(mov)

        # In fixture: exactly 1 hostile raid from '00miska' to city 1000 ('Pentelikon')
        self.assertEqual(len(filtered_attacks), 1)
        raid = filtered_attacks[0]
        self.assertEqual(raid["event"]["missionIconClass"], "piracyRaid")
        self.assertEqual(raid["origin"]["avatarName"], "00miska")
        self.assertEqual(str(raid["target"]["cityId"]), "1000")


if __name__ == "__main__":
    unittest.main()
