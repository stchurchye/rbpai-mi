#!/usr/bin/env bash
# 编译并烧录 ESPHome 固件（需本机安装 esphome CLI）
# 用法:
#   bash flash-esp.sh
#   ESP_PORT=/dev/cu.usbmodem* bash flash-esp.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# 路径含 "-xxx" 时 ESP-IDF 链接器会把片段误当成 gcc 参数，需在无连字符目录编译
BUILD_DIR="${REPO_DIR}"
case "${REPO_DIR}" in
  *-*)
    SAFE_DIR="${HOME}/hwclimate"
    if [[ "${REPO_DIR}" != "${SAFE_DIR}" ]]; then
      echo "==> 检测到路径含连字符，同步到 ${SAFE_DIR} 后编译..."
      mkdir -p "${SAFE_DIR}"
      rsync -a --delete \
        --exclude '.git' --exclude '.esphome' --exclude '.venv-esphome' \
        "${REPO_DIR}/" "${SAFE_DIR}/"
      BUILD_DIR="${SAFE_DIR}"
    fi
    ;;
esac

ESPHOME_DIR="${BUILD_DIR}/firmware/esphome"
YAML="${ESPHOME_DIR}/climate-station.yaml"
SECRETS="${ESPHOME_DIR}/secrets.yaml"

if ! command -v esphome >/dev/null 2>&1; then
  echo "==> 安装 ESPHome CLI..."
  python3 -m pip install --user "esphome>=2024.10.0"
  export PATH="${HOME}/.local/bin:${PATH}"
fi

if [[ ! -f "${SECRETS}" ]]; then
  echo "==> 创建 secrets.yaml（请编辑 WiFi 与 API）"
  cp "${ESPHOME_DIR}/secrets.yaml.example" "${SECRETS}"
  echo "    编辑: ${SECRETS}"
  exit 1
fi

JSON_FILE="${BUILD_DIR}/config/climate_rooms.json"
if [[ -f "${JSON_FILE}" ]]; then
  echo "==> 根据 climate_rooms.json 生成 ESPHome 配置..."
  python3 "${BUILD_DIR}/scripts/generate_climate_config.py" --json "${JSON_FILE}"
elif [[ ! -f "${ESPHOME_DIR}/generated_substitutions.yaml" ]]; then
  echo "错误: 未找到 generated_substitutions.yaml"
  echo "      请先运行: bash scripts/sync-ha-entities.sh"
  exit 1
fi

cd "${ESPHOME_DIR}"
OPTS=(run "${YAML}")
if [[ -n "${ESP_PORT:-}" ]]; then
  OPTS+=(--device "${ESP_PORT}")
fi

echo "==> 编译并烧录 ${YAML}"
esphome "${OPTS[@]}"
