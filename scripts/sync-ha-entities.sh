#!/usr/bin/env bash
# 从 HA 拉取温湿度实体并生成 HA packages + ESPHome 配置
# 用法: bash scripts/sync-ha-entities.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_DIR}/config/ha.env"
JSON_FILE="${REPO_DIR}/config/climate_rooms.json"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "==> 创建 config/ha.env ..."
  cp "${REPO_DIR}/config/ha.env.example" "${ENV_FILE}"
  echo "    请编辑 ${ENV_FILE} 填写 HA_URL 与 HA_TOKEN 后重新运行"
  exit 1
fi

echo "==> 从 Home Assistant 拉取实体..."
python3 "${REPO_DIR}/scripts/fetch_ha_entities.py" --env "${ENV_FILE}" --out "${JSON_FILE}"

echo "==> 生成 packages 与 ESPHome 配置..."
python3 "${REPO_DIR}/scripts/generate_climate_config.py" --json "${JSON_FILE}"

echo ""
echo "完成。可选: 编辑 ${JSON_FILE} 调整房间名后再次运行本脚本"
echo "然后: bash scripts/deploy-ha-packages.sh"
