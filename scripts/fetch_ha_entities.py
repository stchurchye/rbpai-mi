#!/usr/bin/env python3
"""从 Home Assistant REST API 拉取温湿度实体并写入 config/climate_rooms.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "config" / "climate_rooms.json"
DEFAULT_ENV = REPO_ROOT / "config" / "ha.env"

TEMP_MARKERS = ("temperature", "temp")
HUMI_MARKERS = ("humidity", "humid")
# 排除 HA 内生成的模板/统计传感器，只保留物理设备源实体
EXCLUDE_ENTITY_SUBSTRINGS = (
    "qi_hou_zhan",
    "climate_outdoor",
    "backup_",
    "jin_ri_zui_gao",
    "quan_wu_zui_re",
)


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env


def fetch_states(url: str, token: str) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/states",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_excluded_entity(entity_id: str) -> bool:
    eid = entity_id.lower()
    return any(x in eid for x in EXCLUDE_ENTITY_SUBSTRINGS)


def entity_matches_filter(entity_id: str, attrs: dict, filters: list[str]) -> bool:
    if is_excluded_entity(entity_id):
        return False
    if not filters:
        return True
    blob = entity_id.lower()
    for k, v in attrs.items():
        if isinstance(v, str):
            blob += " " + v.lower()
    return any(f in blob for f in filters)


def is_temp_entity(entity_id: str, attrs: dict) -> bool:
    if attrs.get("device_class") == "temperature":
        return True
    eid = entity_id.lower()
    return any(m in eid for m in TEMP_MARKERS) and "humid" not in eid


def is_humi_entity(entity_id: str, attrs: dict) -> bool:
    if attrs.get("device_class") == "humidity":
        return True
    eid = entity_id.lower()
    return any(m in eid for m in HUMI_MARKERS)


def base_key(entity_id: str) -> str:
    """sensor.living_room_temperature -> living_room"""
    eid = entity_id.split(".", 1)[-1].lower()
    for suffix in (
        "_relative_humidity",
        "_temperature",
        "_temp",
        "_humidity",
        "_humid",
    ):
        if eid.endswith(suffix):
            return eid[: -len(suffix)]
    return eid


def friendly_label(name: str, entity_id: str) -> str:
    if name and name not in ("unknown", "unavailable"):
        # 去掉常见后缀
        for suf in (" Temperature", " 温度", " Humidity", " 湿度", "温度", "湿度"):
            if name.endswith(suf):
                return name[: -len(suf)].strip()
        return name.strip()
    key = base_key(entity_id)
    return key.replace("_", " ").title()


def pair_rooms(states: list[dict[str, Any]], filters: list[str]) -> tuple[list[dict], list[dict]]:
    temps: dict[str, dict] = {}
    humis: dict[str, dict] = {}
    unpaired: list[dict] = []

    for st in states:
        eid = st.get("entity_id", "")
        if not eid.startswith("sensor."):
            continue
        attrs = st.get("attributes") or {}
        if not entity_matches_filter(eid, attrs, filters):
            continue

        device_id = attrs.get("device_id") or attrs.get("via_device") or ""
        key = str(device_id) if device_id else base_key(eid)

        if is_temp_entity(eid, attrs):
            temps[key] = st
        elif is_humi_entity(eid, attrs):
            humis[key] = st

    rooms: list[dict] = []
    used_humi: set[str] = set()

    for key, t in sorted(temps.items(), key=lambda x: x[1]["entity_id"]):
        h = humis.get(key)
        label = friendly_label(t.get("attributes", {}).get("friendly_name", ""), t["entity_id"])
        room = {
            "label": label,
            "temp": t["entity_id"],
            "humidity": h["entity_id"] if h else "",
        }
        rooms.append(room)
        if h:
            used_humi.add(key)

    for key, h in humis.items():
        if key not in used_humi and key not in temps:
            unpaired.append(
                {
                    "type": "humidity",
                    "entity_id": h["entity_id"],
                    "label": friendly_label(h.get("attributes", {}).get("friendly_name", ""), h["entity_id"]),
                }
            )

    return rooms, unpaired


def merge_existing(out_path: Path, data: dict) -> dict:
    if not out_path.exists():
        return data
    try:
        old = json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return data

    # 保留用户改过的 label：按 temp entity_id 匹配
    old_labels = {r.get("temp"): r.get("label") for r in old.get("rooms", []) if r.get("temp")}
    for room in data["rooms"]:
        if room["temp"] in old_labels and old_labels[room["temp"]]:
            room["label"] = old_labels[room["temp"]]

    data["notify_service"] = old.get("notify_service", data.get("notify_service"))
    data["outdoor_temp_entity"] = old.get(
        "outdoor_temp_entity", data.get("outdoor_temp_entity")
    )
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch HA climate entities")
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--url", help="Override HA_URL")
    parser.add_argument("--token", help="Override HA_TOKEN")
    parser.add_argument("--filter", help="Comma-separated filter keywords")
    args = parser.parse_args()

    env = load_env(args.env)
    url = args.url or env.get("HA_URL", "")
    token = args.token or env.get("HA_TOKEN", "")
    filt_raw = args.filter if args.filter is not None else env.get("HA_ENTITY_FILTER", "")
    filters = [f.strip().lower() for f in filt_raw.split(",") if f.strip()]

    if not url or not token or "REPLACE_ME" in token:
        print("错误: 请配置 config/ha.env 中的 HA_URL 与 HA_TOKEN", file=sys.stderr)
        return 1

    try:
        states = fetch_states(url, token)
    except urllib.error.HTTPError as e:
        print(f"HTTP 错误: {e.code} {e.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"连接失败: {e.reason}", file=sys.stderr)
        return 1

    rooms, unpaired = pair_rooms(states, filters)
    if not rooms:
        print("警告: 未找到温湿度传感器，请检查 HA 集成与 HA_ENTITY_FILTER", file=sys.stderr)

    data = {
        "rooms": rooms,
        "outdoor_temp_entity": "sensor.climate_outdoor_temp",
        "notify_service": env.get("HA_NOTIFY_SERVICE", "notify.notify"),
        "unpaired": unpaired,
    }
    data = merge_existing(args.out, data)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"已写入 {args.out} — {len(rooms)} 个房间, {len(unpaired)} 个未配对湿度")
    for r in rooms:
        hum = r["humidity"] or "(无湿度)"
        print(f"  · {r['label']}: {r['temp']} / {hum}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
