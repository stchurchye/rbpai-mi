#!/usr/bin/env bash
# 将 packages 同步到已运行的 HA config 目录
# 用法:
#   bash deploy-ha-packages.sh
#   HA_CONFIG=/path/to/config bash deploy-ha-packages.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGES_SRC="${REPO_DIR}/homeassistant/packages"
HA_CONFIG="${HA_CONFIG:-${REPO_DIR}/homeassistant/config}"

if [[ ! -d "${HA_CONFIG}" ]]; then
  echo "错误: HA config 目录不存在: ${HA_CONFIG}"
  echo "      先运行 scripts/setup-ha.sh 或设置 HA_CONFIG 环境变量"
  exit 1
fi

mkdir -p "${HA_CONFIG}/packages"

JSON_FILE="${REPO_DIR}/config/climate_rooms.json"
if [[ -f "${JSON_FILE}" ]]; then
  echo "==> 根据 climate_rooms.json 重新生成 packages..."
  python3 "${REPO_DIR}/scripts/generate_climate_config.py" --json "${JSON_FILE}"
else
  echo "==> 提示: 未找到 config/climate_rooms.json，跳过生成（可先运行 sync-ha-entities.sh）"
fi

cp -f "${PACKAGES_SRC}"/*.yaml "${HA_CONFIG}/packages/"

# 确保 configuration.yaml 包含 packages
CFG="${HA_CONFIG}/configuration.yaml"
if [[ -f "${CFG}" ]] && ! grep -q "include_dir_named packages" "${CFG}"; then
  echo "==> 请在 ${CFG} 的 homeassistant: 下添加:"
  echo "    packages: !include_dir_named packages"
fi

echo "==> 已复制 packages 到 ${HA_CONFIG}/packages/"
echo "    在 HA：开发者工具 → YAML → 检查配置 → 重启 Home Assistant"
