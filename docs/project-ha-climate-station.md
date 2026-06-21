# 家用气候站 — 安装指南（自动化优先）

设计规格：[superpowers/specs/2026-05-22-ha-climate-station-design.md](superpowers/specs/2026-05-22-ha-climate-station-design.md)

---

## 你需要准备

- 树莓派 3（已装 Raspberry Pi OS，能 SSH）
- 与 HA、板子同一 WiFi
- 小米账号（接入 Miot）
- 电脑 + USB-C 线（烧录板子）
- （可选）Nabu Casa 订阅（出门连板子用）
- （P4）云端 STT/LLM/TTS API Key

---

## 第一步：树莓派安装 Home Assistant（一条命令）

在**树莓派**上克隆本仓库或复制 `homeassistant/`、`scripts/` 目录后执行：

```bash
cd /path/to/硬件-cursor
bash scripts/setup-ha.sh
```

浏览器打开：`http://<树莓派IP>:8123`，完成首次创建账号。

---

## 第二步：安装 HACS 与小米温湿度（UI，约 15 分钟）

1. 按 [HACS 官方说明](https://hacs.xyz/docs/setup/download) 安装 HACS  
2. HACS → 集成 → 搜索 **Xiaomi Miot Auto** → 安装  
3. 设置 → 设备与服务 → 添加集成 → **Xiaomi Miot Auto** → 登录小米账号  
4. 勾选全部温湿度计  

在 **开发者工具 → 状态** 搜索 `temperature`，记下实体 ID，例如：

- `sensor.living_room_temperature`

---

## 第三步：自动拉取实体并生成配置（推荐，一条命令）

在**你的电脑**或树莓派上（需能访问 HA）：

```bash
cp config/ha.env.example config/ha.env
# 编辑 ha.env：HA_URL、HA_TOKEN（HA 个人资料 → 长期访问令牌）
bash scripts/sync-ha-entities.sh
```

脚本会：

1. 从 HA 拉取全部温湿度实体 → `config/climate_rooms.json`  
2. 自动生成 `climate_rooms_sensors.yaml`、`climate_rooms_automations.yaml`  
3. 自动生成 ESPHome `generated_substitutions.yaml` 与传感器 package  

可选：编辑 `config/climate_rooms.json` 调整房间中文名，再运行一次 `sync-ha-entities.sh`。

**尚未接 HA 时**：可先用示例数据试生成：

```bash
cp config/climate_rooms.json.example config/climate_rooms.json
python3 scripts/generate_climate_config.py
```

部署到 HA：

```bash
bash scripts/deploy-ha-packages.sh
```

开发者工具 → YAML → **检查配置** → **重启 Home Assistant**。

在 **设置 → 辅助元素** 调整 **高温告警温度**（默认 30°C）。

无需再手改 `entity_id` 列表（除非不用 sync 脚本）。

---

## 第四步：安装手机 App 与天气（可选）

1. 手机安装 **Home Assistant** App，登录同一账号  
2. 设置 → 设备与服务 → 添加 **和风天气**（或其它天气）  
3. 确认存在 `sensor.climate_outdoor_temp` 或修改 `climate_sensors.yaml` 中室外温度模板  

编辑 `config/ha.env` 中的 `HA_NOTIFY_SERVICE`（如 `notify.mobile_app_iphone`），重新 `sync-ha-entities.sh` 即可更新推送服务。

---

## 第五步：烧录 RLCD 板子

在**你的电脑**上（已装 Python 3）：

```bash
cd /path/to/硬件-cursor/firmware/esphome
cp secrets.yaml.example secrets.yaml
# 编辑 secrets.yaml：WiFi
```

确认已运行过 `sync-ha-entities.sh`（或示例 JSON 生成），存在 `generated_substitutions.yaml`。

生成 API 密钥（首次）：

```bash
pip install "esphome>=2024.10.0"
cd /path/to/硬件-cursor
esphome secrets generate-key firmware/esphome/secrets.yaml api_encryption_key
```

烧录（USB 连接板子，按住 BOOT 上电进入下载模式）：

```bash
bash scripts/flash-esp.sh
# 或指定串口: ESP_PORT=/dev/cu.usbserial-xxx bash scripts/flash-esp.sh
```

---

## 第六步：板子接入 Home Assistant

1. HA → 设置 → 设备与服务 → 添加集成 → **ESPHome**  
2. 输入板子 IP（串口日志或路由器 DHCP 列表）  
3. 输入 API 加密密钥（与 `secrets.yaml` 中 `api_encryption_key` 一致）  

确认：

- 出现设备 **气候站**  
- 服务列表有 `esphome.climate_station_local_alarm`  

手动测试告警：开发者工具 → 服务 → `esphome.climate_station_local_alarm` → 填 `room` / `temp` → 调用，板子应闪屏。

---

## 第七步：Nabu Casa（出门用，可选）

1. HA → 设置 → Home Assistant Cloud → 开始试用/订阅  
2. 按向导启用远程访问  
3. ESPHome 设备在 Cloud 配对后，板子连外网 WiFi 仍可显示家里数据  

**不要**把 8123 端口映射到公网。

---

## 第八步：语音助手（按住 BOOT 说话）

板子有 **两个键**（都在 PCB 上，侧/顶小按键）：

| 按键 | 位置 | 当前功能 |
|------|------|----------|
| **BOOT** | GPIO0，通常靠近 USB | **按住说话，松开结束** |
| **KEY** | GPIO18，用户功能键 | **点按翻页**（切换 6 个房间） |

固件已接入 **Home Assistant Voice Assistant**（录音在板子，识别/对话/朗读在 HA 云端流水线）。

### 1. 在 HA 配置语音流水线

**百炼 STT + 百炼 TTS**（国内直连，同一把 Key）+ **LLM 任选**（DeepSeek / Qwen 等）。

详细步骤见 [`docs/voice-assistant-setup.md`](voice-assistant-setup.md)。

概要：

1. `bash scripts/install-voice-components.sh church@192.168.31.155`
2. 添加集成：**Aliyun BaiLian STT**、**Aliyun BaiLian TTS**（百炼 Key）
3. 添加 **OpenAI 对话**：DeepSeek（`https://api.deepseek.com/v1`）或百炼 Qwen
4. 创建助手 `pi-voice`：STT=百炼 STT，TTS=百炼 TTS，对话=OpenAI

### 2. 把助手分配给气候站

1. **设置 → 设备与服务 → ESPHome → 气候站**
2. 找到 **Voice Assistant** / 助手配置，选择刚创建的助手

### 3. 使用

1. **按住 BOOT** → 屏幕显示「正在听...」→ 说话 → **松开**
2. 等几秒 → 板子扬声器播放 HA 返回的回答

### 故障

| 现象 | 处理 |
|------|------|
| KEY 没反应 | 点按 KEY（不是 BOOT）；屏幕应切到下一页 |
| 按住 BOOT 无「正在听」 | 确认 HA 与板子在线；重新 OTA 最新固件 |
| 能听不说 | 检查 HA 语音流水线 TTS、GPIO46 功放已开 |
| 想用云端直连 DeepSeek | 见 `firmware/esphome/voice_p4.yaml.example`（高级） |

---

## 第九步：语音 + LLM 直连板子（P4 可选，未默认启用）

### 语音识别在哪里做？

| 环节 | 位置 |
|------|------|
| 录音 | **板子本地**（麦克风） |
| STT 语音→文字 | **云端**（P4 实现，ESP32 无法完整离线中文识别） |
| LLM 对话 | **云端 DeepSeek**（推荐） |
| TTS 朗读 | **云端**（Edge TTS / 讯飞等） |

当前固件已留扩展位。完整语音需追加：

- `i2s_audio` + `microphone` + `speaker`（ES8311/ES7210）  
- `http_request` 调用 STT / DeepSeek / TTS API  

参考：[Waveshare ESP32-S3-RLCD-4.2 ESPHome 设备页](https://devices.esphome.io/devices/waveshare-esp32-s3-rlcd-42/)

---

## 验收清单

- [ ] HA 中 6+ 路小米温湿度有数据  
- [ ] 修改「高温告警温度」后，自动化使用新阈值  
- [ ] 超温 2 分钟 → 手机通知  
- [ ] 超温 → 板子闪屏（`local_alarm` 服务）  
- [ ] 板子摘要页显示最热房间、室外、告警线  
- [ ] （可选）Nabu Casa 出门可连  

---

## 故障排查

| 现象 | 处理 |
|------|------|
| 板子显示「未连HA」 | 确认 ESPHome 集成在线、实体 ID 正确、同一 WiFi |
| 自动化不推送 | 检查 `notify` 服务名；先用 `notify.notify` 测试 |
| `local_alarm` 无反应 | HA 服务名须为 `esphome.climate_station_local_alarm` |
| 编译失败 | 确认 ESPHome ≥ 2024.10；PSRAM 配置与 yaml 中 esp32 段一致 |
| 未找到温湿度实体 | 检查 Miot 是否接入；调整 `ha.env` 中 `HA_ENTITY_FILTER` |
| sync 后 HA 报错 | 开发者工具 → 检查配置；查看 `climate_rooms_*.yaml` |
