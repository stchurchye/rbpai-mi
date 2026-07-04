# AGENTS.md

## 项目概述

**rbpai-mi** 是 Waveshare ESP32-S3-RLCD-4.2 家用气候站 + Home Assistant 集成项目。用低功耗显示屏常显多房间温湿度，与树莓派 HA 联动实现可配置告警、手机推送、语音助手（国内云服务支持）。

---

## 架构与关键目录

```
rbpai-mi/
├── firmware/esphome/
│   ├── climate-station.yaml              # 主配置，包含 I2S 音频、ST7305 屏、HA API
│   ├── generated_substitutions.yaml      # 由 sync-ha-entities.sh 生成（room_id→sensor 映射）
│   ├── generated/climate_ha_sensors.yaml # 自动生成的传感器 package
│   ├── includes/
│   │   ├── voice_assistant.yaml          # 云端语音流水线（百炼 STT + DeepSeek/Qwen LLM + TTS）
│   │   └── battery.yaml                  # 18650 电压采样 + 百分比模板
│   ├── secrets.yaml.example              # WiFi、HA API Key（勿入 git）
│   ├── entities.yaml.example             # 房间实体 ID 列表（用户手填或 sync 自动生成）
│   └── external_components/              # 本地驱动（ES8311 Codec、I2S Audio、ST7305 RLCD）
├── homeassistant/
│   ├── docker-compose.yml                # Pi3 Docker 部署（8123、BlueZ/D-Bus for Bluetooth）
│   ├── config/                           # HA 配置文件夹（含 automations/packages）
│   └── packages/
│       ├── climate_helpers.yaml          # input_number（温度告警阈值）
│       ├── climate_sensors.yaml          # 模板：最热房间、室外温差、日最高
│       └── climate_automations.yaml      # 告警自动化（触发 notify + esphome.local_alarm）
├── scripts/
│   ├── sync-ha-entities.sh               # 拉取 HA 实体、生成 ESPHome 配置、HA packages
│   ├── fetch_ha_entities.py              # REST API 查询温湿度实体 → JSON
│   ├── generate_climate_config.py        # 根据 JSON 生成 YAML
│   ├── flash-esp.sh                      # 编译烧录 ESPHome（路径含 "-" 时自动同步到无连字符目录）
│   ├── setup-ha.sh                       # Pi 一键装 HA（docker、权限）
│   └── deploy-ha-packages.sh             # 复制生成的 packages 到 HA config
├── config/
│   ├── ha.env.example                    # HA_URL、HA_TOKEN、notify 服务名（用户需 cp → ha.env）
│   └── climate_rooms.json                # room_id ↔ 中文名、sensor entity_id 映射（可手编）
└── docs/
    ├── hardware-esp32s3-rlcd.md          # 完整硬件文档：引脚、规格、安装安全、应用场景
    ├── project-ha-climate-station.md     # 用户操作指南（8 步）
    ├── voice-assistant-setup.md          # 百炼 STT/TTS + DeepSeek 配置步骤
    └── superpowers/specs/2026-05-22-ha-climate-station-design.md # 设计规格（架构、职责、分期）
```

### 数据流概览

1. **小米温湿度采集**：米家设备 → Home Assistant Miot Auto 集成 → `sensor.<room>_temperature` / `humidity`
2. **HA 侧处理**：模板传感器计算日最高、室外差值 → `input_number.climate_alert_threshold`（用户可配）
3. **告警自动化**：温度超阈 2 分钟 → `notify.mobile_app_*`（手机推送）+ `esphome.climate_station_local_alarm` 服务调用
4. **板子显示**：订阅 HA 实体（API）→ RLCD 常显摘要页（最热、今日最高、告警线）+ 分页列表
5. **语音链路**：按住 BOOT 录音 → `voice_assistant` → HA 云端（STT/LLM/TTS） → 扬声器播放
6. **出门远程**：Nabu Casa 加密隧道 → 板子连外网 WiFi 仍可同步家里数据（可选订阅）

---

## 上手与常用命令

### 环境要求
- 树莓派 3（Raspberry Pi OS）+ 基础 Docker
- 电脑（Python 3.8+）+ USB-C 线（烧录）
- 小米账号（接入温湿度计）
- HA URL + 长期访问令牌

### 第一次上手

```bash
# 1. Pi 上一键装 HA（Docker）
bash scripts/setup-ha.sh

# 2. 在 HA 中安装 Xiaomi Miot Auto，接入小米温湿度

# 3. 电脑：配置 ha.env（HA_URL、HA_TOKEN）
cp config/ha.env.example config/ha.env
# 编辑 config/ha.env 填入 URL 和 token

# 4. 自动拉取实体、生成配置
bash scripts/sync-ha-entities.sh

# 5. 部署 HA packages（自动化、模板传感器）
bash scripts/deploy-ha-packages.sh

# 6. 电脑：烧录 ESP32（USB 连接板子，按住 BOOT 进下载模式）
bash scripts/flash-esp.sh
# 或指定串口：ESP_PORT=/dev/cu.usbserial-xxx bash scripts/flash-esp.sh
```

### 常用操作

| 需求 | 命令 | 说明 |
|------|------|------|
| 添加新房间或编辑名字 | 编辑 `config/climate_rooms.json`，重新 `sync-ha-entities.sh` | 自动重新生成 HA packages + ESPHome config |
| 修改告警温度 | HA UI → 设置 → 辅助元素 → 高温告警温度 | 实时生效，自动化订阅该值 |
| 重新烧录固件 | `bash scripts/flash-esp.sh` | ESPHome 编译 → 烧录；需 USB 连接 |
| 查看板子日志 | `esphome logs firmware/esphome/climate-station.yaml` | 需本机装 `esphome >= 2024.10.0` |
| 本地测试告警 | HA 开发者工具 → 服务 → `esphome.climate_station_local_alarm` → 填 `{"room": "客厅", "temp": 35}` 调用 | 板子应闪屏 + 蜂鸣 |
| 配置语音助手 | `bash scripts/install-voice-components.sh <pi-user@pi-ip>` + 见 `docs/voice-assistant-setup.md` | P4 功能，需百炼 API Key |

---

## ⚠️ 坑与不变式

1. **路径含连字符会烧录失败**  
   ESP-IDF 链接器误把 `-xxx` 当 gcc 参数。`flash-esp.sh` 自动检测并同步到 `~/hwclimate` 编译，勿手改或重命名仓库目录名。

2. **生成物勿手改，重新 sync 覆盖**  
   - `firmware/esphome/generated_substitutions.yaml`
   - `firmware/esphome/generated/`
   - `homeassistant/packages/climate_rooms_*.yaml`  
   这些由 `sync-ha-entities.sh` 生成，手改会被覆盖；需修改源则编辑 `config/climate_rooms.json` 或脚本。

3. **secrets.yaml + ha.env 勿入 git**  
   `.gitignore` 已覆盖，但勿手动 `git add -f` 密钥文件；CI/CD 或分享代码时务必剔除。

4. **RLCD 屏幕脆弱**  
   装电池、插 USB 时勿压屏（会损坏）；损坏不在保修范围内（官方说明）。

5. **RTC 备电电池仅支持可充电型**  
   接口 PH1.0，勿使用一次性纽扣电池替代；需要充放电管理。

6. **SD 卡无硬件卡检测**  
   GPIO17（SD_CD）未接，启动时挂载或避免热插拔；固件已处理，无需手改。

7. **ESPHome 编译需足够空间与网络**  
   首次编译下载 esp-idf v5.5.2（~1GB），确保网络稳定；`.esphome/` 缓存勿删除以加速二次编译。

---

## ⚠️ 安全约束

### 固件烧录

- ⚠️ **不可逆操作**：烧录会覆盖原固件，确认目标设备与 `climate-station.yaml` 的设备名一致再烧。
- ⚠️ **下载模式进入**：按住 BOOT 再上电（或复位），勿按错 PWR 键导致误操作。
- ⚠️ **USB 连接稳定性**：烧录中插拔 USB 可能导致固件损坏；成功后板子正常启动。

### 密钥与通信

- ⚠️ **secrets.yaml + ha.env 绝不进 git**：含 WiFi 密码、HA token、云服务 API Key。
  - 本地 `.gitignore` 已覆盖，但分享代码前务必 `git check-ignore` 验证。
  - 若不慎提交，立即重置 token 与 API Key。
- ⚠️ **API 加密密钥**：`api_encryption_key` 需保存；烧录后改密则需重新配对。
- ⚠️ **Nabu Casa 替代品**：勿将 HA `8123` 端口映射公网（frp、DMZ、端口转发等），改用官方 Nabu Casa 订阅。

### 电源与硬件

- ⚠️ **18650 电池反接告警**：板上 WRN 灯亮 → 立即拔电检查极性；长期反接损伤电池管理芯片。
- ⚠️ **RTC 备电接口**：仅供 PCF85063 计时，不为主系统供电；更换电池时注意极性。
- ⚠️ **GPIO 复用冲突**：BOOT（GPIO0）与 KEY（GPIO18）复用部分扩展排针，扩展外设时检查原理图避免冲突。

### 云服务依赖

- **语音助手（P4）需云端 API**：
  - STT：百炼（阿里） / Whisper（OpenAI）
  - LLM：DeepSeek / 阿里通义 / OpenAI（根据 system prompt 支持）
  - TTS：百炼 / Edge TTS
  - 若 API Key 泄露或配额耗尽，语音功能失效；HA 与屏幕显示无碍。

---

## 参考资源

| 资源 | 链接 | 用途 |
|------|------|------|
| 硬件官方 Wiki | https://docs.waveshare.com/ESP32-S3-RLCD-4.2 | 引脚、规格、示例 |
| 示例工程 | https://github.com/waveshareteam/ESP32-S3-RLCD-4.2 | ESP-IDF / Arduino 参考 |
| ESPHome 文档 | https://esphome.io/components/index.html | 组件配置 |
| Home Assistant | https://www.home-assistant.io/docs/ | HA 配置、自动化、集成 |
| Nabu Casa | https://www.nabucasa.com/ | 远程访问方案 |
| 百炼 STT/TTS | https://dashscope.aliyuncs.com/ | 语音识别与合成 |
| DeepSeek API | https://api.deepseek.com | LLM 对话 |
"