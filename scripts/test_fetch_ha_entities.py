#!/usr/bin/env python3
"""fetch_ha_entities.pair_rooms 单元测试（mock 数据，无需 HA）."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_ha_entities import pair_rooms  # noqa: E402


def test_pair_by_device_id() -> None:
    states = [
        {
            "entity_id": "sensor.living_room_temperature",
            "attributes": {"device_class": "temperature", "device_id": "dev1", "friendly_name": "客厅 Temperature"},
        },
        {
            "entity_id": "sensor.living_room_humidity",
            "attributes": {"device_class": "humidity", "device_id": "dev1", "friendly_name": "客厅 Humidity"},
        },
        {
            "entity_id": "sensor.bedroom_temperature",
            "attributes": {"device_class": "temperature", "device_id": "dev2", "friendly_name": "卧室 Temperature"},
        },
    ]
    rooms, unpaired = pair_rooms(states, [])
    assert len(rooms) == 2
    temps = {r["temp"] for r in rooms}
    assert "sensor.living_room_temperature" in temps
    assert "sensor.bedroom_temperature" in temps
    living = next(r for r in rooms if r["temp"] == "sensor.living_room_temperature")
    assert living["humidity"] == "sensor.living_room_humidity"
    assert unpaired == []


def test_filter_xiaomi() -> None:
    states = [
        {
            "entity_id": "sensor.other_temperature",
            "attributes": {"device_class": "temperature", "friendly_name": "Other"},
        },
        {
            "entity_id": "sensor.xiaomi_kitchen_temperature",
            "attributes": {"device_class": "temperature", "friendly_name": "Kitchen"},
        },
    ]
    rooms, _ = pair_rooms(states, ["xiaomi"])
    assert len(rooms) == 1
    assert "xiaomi" in rooms[0]["temp"]


if __name__ == "__main__":
    test_pair_by_device_id()
    test_filter_xiaomi()
    print("fetch_ha_entities tests OK")
