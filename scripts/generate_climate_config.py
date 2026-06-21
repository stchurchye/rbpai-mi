#!/usr/bin/env python3
"""从 config/climate_rooms.json 生成 HA packages 与 ESPHome 配置."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON = REPO_ROOT / "config" / "climate_rooms.json"
MAX_ESPHOME_ROOMS = 8

# 将源传感器读数统一为 °C（小米 Miot 常为 °F）
TEMP_TO_CELSIUS = """          {{% set raw = states('{eid}') %}}
          {{% set v = raw | float(none) %}}
          {{% set u = state_attr('{eid}', 'unit_of_measurement') | default('') %}}
          {{% if v is none or raw in ['unavailable', 'unknown', 'none', ''] %}}
            unavailable
          {{% elif u in ['°F', 'F', '℉'] %}}
            {{{{ ((v - 32) * 5 / 9) | round(1) }}}}
          {{% else %}}
            {{{{ v | round(1) }}}}
          {{% endif %}}"""

TEMP_ATTR_MAX_TO_CELSIUS = """          {{% set raw = state_attr('{eid}', 'max') | default(states('{eid}')) | string %}}
          {{% set v = raw | float(none) %}}
          {{% set u = state_attr('{eid}', 'unit_of_measurement') | default('') %}}
          {{% if v is none or raw in ['unavailable', 'unknown', 'none', ''] %}}
            unavailable
          {{% elif u in ['°F', 'F', '℉'] %}}
            {{{{ ((v - 32) * 5 / 9) | round(1) }}}}
          {{% else %}}
            {{{{ v | round(1) }}}}
          {{% endif %}}"""

TEMP_ATTR_MIN_TO_CELSIUS = """          {{% set raw = state_attr('{eid}', 'min') | default(states('{eid}')) | string %}}
          {{% set v = raw | float(none) %}}
          {{% set u = state_attr('{eid}', 'unit_of_measurement') | default('') %}}
          {{% if v is none or raw in ['unavailable', 'unknown', 'none', ''] %}}
            unavailable
          {{% elif u in ['°F', 'F', '℉'] %}}
            {{{{ ((v - 32) * 5 / 9) | round(1) }}}}
          {{% else %}}
            {{{{ v | round(1) }}}}
          {{% endif %}}"""


def max_today_entity(index: int) -> str:
    return f"sensor.climate_room_{index}_max_today"


def min_today_entity(index: int) -> str:
    return f"sensor.climate_room_{index}_min_today"


def temp_c_entity(index: int) -> str:
    return f"sensor.climate_room_{index}_temp_c"

PKG_SENSORS = REPO_ROOT / "homeassistant" / "packages" / "climate_rooms_sensors.yaml"
PKG_AUTO = REPO_ROOT / "homeassistant" / "packages" / "climate_rooms_automations.yaml"
ESP_SUBS = REPO_ROOT / "firmware" / "esphome" / "generated_substitutions.yaml"
ESP_SENSORS = REPO_ROOT / "firmware" / "esphome" / "generated" / "climate_ha_sensors.yaml"


def slug(s: str) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", s.lower())
    return s.strip("_") or "room"


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"未找到 {path}，请先运行 fetch_ha_entities.py")
    return json.loads(path.read_text(encoding="utf-8"))


def gen_ha_sensors(cfg: dict) -> str:
    rooms = cfg.get("rooms", [])
    lines = [
        "# AUTO-GENERATED — 勿手改，运行 scripts/generate_climate_config.py 重新生成",
        "",
        "template:",
        "  - sensor:",
    ]

    display_ids: list[str] = []
    room_map_lines: list[str] = []

    for i, room in enumerate(rooms):
        label = room["label"]
        temp = room["temp"]
        uid = f"room_{i + 1}"
        display = temp_c_entity(i + 1)
        display_ids.append(display)
        room_map_lines.append(f"            '{label}': '{display}',")

        celsius_tpl = TEMP_TO_CELSIUS.format(eid=temp)

        lines.extend(
            [
                f"      - name: \"Climate Room {i + 1} Temp C\"",
                f"        unique_id: climate_{uid}_temp_c",
                f"        unit_of_measurement: \"°C\"",
                f"        device_class: temperature",
                f"        state: >",
                TEMP_TO_CELSIUS.format(eid=temp),
            ]
        )

        lines.extend(
            [
                "",
                f"      - name: \"气候站_{label}_与室外差\"",
                f"        unique_id: climate_{uid}_delta",
                f"        unit_of_measurement: \"°C\"",
                f"        state: >",
                f"          {{% set in_t = states('{display}') | float(none) %}}",
                f"          {{% set out_t = states('sensor.climate_outdoor_temp') | float(none) %}}",
                f"          {{% if in_t is not none and out_t is not none %}}",
                f"            {{{{ (in_t - out_t) | round(1) }}}}",
                f"          {{% else %}}",
                f"            unavailable",
                f"          {{% endif %}}",
                "",
            ]
        )

    ids_yaml = ",\n            ".join(f"'{x}'" for x in display_ids)
    map_yaml = "\n".join(room_map_lines)

    lines.extend(
        [
            "      - name: \"气候站_全屋最热温度\"",
            "        unique_id: climate_hottest_temp",
            "        unit_of_measurement: \"°C\"",
            "        device_class: temperature",
            "        state: >",
            "          {% set ids = [",
            f"            {ids_yaml}",
            "          ] %}",
            "          {% set ns = namespace(max=none) %}",
            "          {% for eid in ids %}",
            "            {% set v = states(eid) | float(none) %}",
            "            {% if v is not none and (ns.max is none or v > ns.max) %}",
            "              {% set ns.max = v %}",
            "            {% endif %}",
            "          {% endfor %}",
            "          {{ ns.max if ns.max is not none else 'unknown' }}",
            "",
            "      - name: \"气候站_全屋最热房间\"",
            "        unique_id: climate_hottest_room",
            "        state: >",
            "          {% set ids = {",
            map_yaml,
            "          } %}",
            "          {% set ns = namespace(name='—', max=-99) %}",
            "          {% for room, eid in ids.items() %}",
            "            {% set v = states(eid) | float(none) %}",
            "            {% if v is not none and v > ns.max %}",
            "              {% set ns.max = v %}",
            "              {% set ns.name = room %}",
            "            {% endif %}",
            "          {% endfor %}",
            "          {{ ns.name }}",
            "",
        ]
    )

    stat_lines = [
        "",
        "sensor:",
    ]
    for i in range(len(rooms)):
        uid = temp_c_entity(i + 1)
        stat_lines.extend(
            [
                "  - platform: statistics",
                f"    entity_id: {uid}",
                f"    name: Climate Room {i + 1} Max Today",
                f"    unique_id: climate_room_{i + 1}_max_today",
                "    state_characteristic: value_max",
                "    max_age:",
                "      hours: 24",
                "    sampling_size: 1440",
                "  - platform: statistics",
                f"    entity_id: {uid}",
                f"    name: Climate Room {i + 1} Min Today",
                f"    unique_id: climate_room_{i + 1}_min_today",
                "    state_characteristic: value_min",
                "    max_age:",
                "      hours: 24",
                "    sampling_size: 1440",
            ]
        )

    return "\n".join(lines) + "\n" + "\n".join(stat_lines) + "\n"


def gen_ha_automations(cfg: dict) -> str:
    rooms = cfg.get("rooms", [])
    notify = cfg.get("notify_service", "notify.notify")
    entity_lines = "\n".join(
        f"          - {temp_c_entity(i + 1)}" for i in range(len(rooms))
    )

    return f"""# AUTO-GENERATED — 勿手改

automation:
  - id: climate_high_temperature_alert
    alias: "气候站_高温告警"
    description: "任一路温度超过 input_number 阈值时推送手机并触发 ESP 本地告警"
    mode: queued
    max: 5
    trigger:
      - platform: numeric_state
        entity_id:
{entity_lines}
        above: input_number.climate_alert_threshold
        for:
          minutes: 2
    condition:
      - condition: state
        entity_id: input_boolean.climate_alert_enabled
        state: "on"
    action:
      - variables:
          room_name: "{{{{ trigger.to_state.attributes.friendly_name | default(trigger.entity_id) }}}}"
          temp_val: "{{{{ trigger.to_state.state }}}}"
      - service: {notify}
        data:
          title: "高温告警"
          message: "{{{{ room_name }}}} 已达 {{{{ temp_val }}}}°C（阈值 {{{{ states('input_number.climate_alert_threshold') }}}}°C）"
        continue_on_error: true
      - condition: template
        value_template: >
          {{% if is_state('input_boolean.climate_alert_night_mute_sound', 'on') %}}
            {{% set h = now().hour %}}
            {{{{ not (h >= 22 or h < 7) }}}}
          {{% else %}}
            true
          {{% endif %}}
      - service: esphome.climate_station_local_alarm
        data:
          room: "{{{{ room_name }}}}"
          temp: "{{{{ temp_val }}}}"
        continue_on_error: true
"""


def gen_esphome_substitutions(cfg: dict) -> str:
    rooms = cfg.get("rooms", [])
    n = min(len(rooms), MAX_ESPHOME_ROOMS)
    if len(rooms) > MAX_ESPHOME_ROOMS:
        print(
            f"警告: ESPHome 最多显示 {MAX_ESPHOME_ROOMS} 路，其余 {len(rooms) - MAX_ESPHOME_ROOMS} 路仅在 HA 告警",
            file=sys.stderr,
        )

    lines = [
        "# AUTO-GENERATED — 由 generate_climate_config.py 生成",
        "device_name: climate-station",
        'friendly_name: "气候站"',
        f"room_count: \"{n}\"",
        f"display_page_count: \"1\"",
        f"outdoor_temp: {cfg.get('outdoor_temp_entity', 'sensor.climate_outdoor_temp')}",
        "hottest_temp: sensor.climate_hottest_temp",
        "hottest_room: sensor.climate_hottest_room",
        "alert_threshold: input_number.climate_alert_threshold",
    ]

    ui_chars = (
        "0123456789.-度% "
        "气候站总览最热室外告警未连湿度正在听按住说话刷新房间高低今"
        "请检查网络连接点按超其他花房区低高已"
        "模拟安第斯山脉温室监控"
        "语音交互识别思考播报失败中松开结束录音"
        "充电尽快"
    )
    label_chars = "".join(r["label"] for r in rooms[:n])
    glyph_set = "".join(dict.fromkeys(ui_chars + label_chars))
    lines.append(f'font_glyphs: "{glyph_set}"')

    highlight_labels = cfg.get(
        "display_highlight",
        ["花房门口", "花房外面", "西雷丽", "中心"],
    )
    label_to_idx = {r["label"]: i + 1 for i, r in enumerate(rooms[:n])}
    hi_idx = [str(label_to_idx[l]) for l in highlight_labels if l in label_to_idx]
    norm_idx = [
        str(i + 1) for i, r in enumerate(rooms[:n]) if r["label"] not in highlight_labels
    ]
    lines.append(f"highlight_room_indices: \"{', '.join(hi_idx)}\"")
    lines.append(f"normal_room_indices: \"{', '.join(norm_idx)}\"")

    for i in range(1, MAX_ESPHOME_ROOMS + 1):
        if i <= n:
            r = rooms[i - 1]
            hum = r.get("humidity") or r["temp"]
            lines.append(f'room{i}_label: "{r["label"]}"')
            lines.append(f"room{i}_temp: {temp_c_entity(i)}")
            lines.append(f"room{i}_humi: {hum}")
            lines.append(f"room{i}_max: {max_today_entity(i)}")
            lines.append(f"room{i}_min: {min_today_entity(i)}")
        else:
            lines.append(f'room{i}_label: ""')
            lines.append(f"room{i}_temp: sensor.climate_outdoor_temp")
            lines.append(f"room{i}_humi: sensor.climate_outdoor_temp")
            lines.append(f"room{i}_max: sensor.climate_outdoor_temp")
            lines.append(f"room{i}_min: sensor.climate_outdoor_temp")

    return "\n".join(lines) + "\n"


def gen_esphome_sensors(cfg: dict) -> str:
    rooms = cfg.get("rooms", [])
    n = min(len(rooms), MAX_ESPHOME_ROOMS)

    lines = [
        "# AUTO-GENERATED — ESPHome package: HA 传感器订阅",
        "",
        "sensor:",
    ]

    for i in range(1, MAX_ESPHOME_ROOMS + 1):
        if i <= n:
            r = rooms[i - 1]
            hum = r.get("humidity") or r["temp"]
            lines.extend(
                [
                    "  - platform: homeassistant",
                    f"    id: ha_room{i}_temp",
                    f"    entity_id: ${'{'}room{i}_temp{'}'}",
                    "    internal: true",
                    "  - platform: homeassistant",
                    f"    id: ha_room{i}_humi",
                    f"    entity_id: ${'{'}room{i}_humi{'}'}",
                    "    internal: true",
                    "  - platform: homeassistant",
                    f"    id: ha_room{i}_max",
                    f"    entity_id: ${'{'}room{i}_max{'}'}",
                    "    internal: true",
                    "  - platform: homeassistant",
                    f"    id: ha_room{i}_min",
                    f"    entity_id: ${'{'}room{i}_min{'}'}",
                    "    internal: true",
                ]
            )
        else:
            lines.extend(
                [
                    "  - platform: template",
                    f"    id: ha_room{i}_temp",
                    "    lambda: 'return NAN;'",
                    "    internal: true",
                    "  - platform: template",
                    f"    id: ha_room{i}_humi",
                    "    lambda: 'return NAN;'",
                    "    internal: true",
                    "  - platform: template",
                    f"    id: ha_room{i}_max",
                    "    lambda: 'return NAN;'",
                    "    internal: true",
                    "  - platform: template",
                    f"    id: ha_room{i}_min",
                    "    lambda: 'return NAN;'",
                    "    internal: true",
                ]
            )

    lines.extend(
        [
            "  - platform: homeassistant",
            "    id: ha_outdoor_temp",
            "    entity_id: ${outdoor_temp}",
            "    internal: true",
            "  - platform: homeassistant",
            "    id: ha_hottest_temp",
            "    entity_id: ${hottest_temp}",
            "    internal: true",
            "  - platform: homeassistant",
            "    id: ha_alert_threshold",
            "    entity_id: ${alert_threshold}",
            "    internal: true",
            "",
            "text_sensor:",
            "  - platform: homeassistant",
            "    id: ha_hottest_room_text",
            "    entity_id: ${hottest_room}",
            "    internal: true",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate HA/ESPHome climate configs")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args()

    try:
        cfg = load_config(args.json)
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    if not cfg.get("rooms"):
        print("错误: climate_rooms.json 中 rooms 为空", file=sys.stderr)
        return 1

    PKG_SENSORS.write_text(gen_ha_sensors(cfg), encoding="utf-8")
    PKG_AUTO.write_text(gen_ha_automations(cfg), encoding="utf-8")
    ESP_SUBS.write_text(gen_esphome_substitutions(cfg), encoding="utf-8")
    ESP_SENSORS.parent.mkdir(parents=True, exist_ok=True)
    ESP_SENSORS.write_text(gen_esphome_sensors(cfg), encoding="utf-8")

    print(f"已生成:\n  {PKG_SENSORS}\n  {PKG_AUTO}\n  {ESP_SUBS}\n  {ESP_SENSORS}")
    print(f"  房间数: {len(cfg['rooms'])} (ESPHome 显示前 {min(len(cfg['rooms']), MAX_ESPHOME_ROOMS)} 路)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
