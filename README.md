# Waveshare ESP32-S3-RLCD-4.2

| 文档 | 说明 |
|------|------|
| [硬件技术文档](docs/hardware-esp32s3-rlcd.md) | 引脚、规格、ESP-IDF |
| [家用气候站设计](docs/superpowers/specs/2026-05-22-ha-climate-station-design.md) | HA + 小米温湿度 + 告警 + 语音 |
| [气候站安装指南](docs/project-ha-climate-station.md) | `sync-ha-entities.sh` 一键拉实体 + 生成配置 |

```bash
# 接好 HA 与小米后，在电脑上：
cp config/ha.env.example config/ha.env   # 填 URL + Token
bash scripts/sync-ha-entities.sh
bash scripts/deploy-ha-packages.sh
```

官方 Wiki：<https://docs.waveshare.com/ESP32-S3-RLCD-4.2>
