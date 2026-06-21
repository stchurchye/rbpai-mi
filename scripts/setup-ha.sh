#!/usr/bin/env bash
# 在树莓派上安装并启动 Home Assistant（Docker）
# 用法: bash setup-ha.sh
# 建议: curl -fsSL <raw-url>/scripts/setup-ha.sh | bash

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HA_DIR="${REPO_DIR}/homeassistant"
CONFIG_DIR="${HA_DIR}/config"
PACKAGES_SRC="${HA_DIR}/packages"

echo "==> 气候站 HA 安装"
echo "    目录: ${HA_DIR}"

if ! command -v docker >/dev/null 2>&1; then
  echo "==> 安装 Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "${USER}" || true
  echo "    若提示权限不足，请执行: newgrp docker  或重新登录后再运行本脚本"
fi

if ! docker compose version >/dev/null 2>&1 && ! docker-compose version >/dev/null 2>&1; then
  echo "错误: 未找到 docker compose"
  exit 1
fi

COMPOSE="docker compose"
if ! docker compose version >/dev/null 2>&1; then
  COMPOSE="docker-compose"
fi

mkdir -p "${CONFIG_DIR}/packages"

if [[ ! -f "${CONFIG_DIR}/configuration.yaml" ]]; then
  echo "==> 写入默认 configuration.yaml"
  cp "${HA_DIR}/config/configuration.yaml" "${CONFIG_DIR}/configuration.yaml" 2>/dev/null || true
fi

echo "==> 部署 packages..."
cp -f "${PACKAGES_SRC}"/*.yaml "${CONFIG_DIR}/packages/"

echo "==> 启动 Home Assistant..."
cd "${HA_DIR}"
${COMPOSE} pull
${COMPOSE} up -d

IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo ""
echo "=============================================="
echo "  Home Assistant 已启动"
echo "  浏览器打开: http://${IP:-<树莓派IP>}:8123"
echo "  首次访问请创建账号，然后："
echo "    1. 安装 HACS → Xiaomi Miot Auto"
echo "    2. 修改 config/packages 内实体 ID"
echo "    3. 设置 → 辅助元素 → 调整「高温告警温度」"
echo "  详细步骤: docs/project-ha-climate-station.md"
echo "=============================================="
