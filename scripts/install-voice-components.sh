#!/usr/bin/env bash
# 安装 HA 语音 custom components：百炼 TTS + 百炼 STT
# 用法:
#   bash scripts/install-voice-components.sh
#   bash scripts/install-voice-components.sh church@192.168.31.155

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${1:-}"
HA_CONFIG="${HA_CONFIG:-${REPO_DIR}/homeassistant/config}"
TTS_REPO="https://github.com/itning/hass-aliyun_bailian_tts.git"
STT_SRC="${REPO_DIR}/homeassistant/custom_components/aliyun_bailian_stt"

install_local() {
  local cfg="$1"
  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "${tmp}"' EXIT

  echo "==> 安装 Aliyun BaiLian TTS"
  git clone --depth 1 "${TTS_REPO}" "${tmp}/tts-repo"
  mkdir -p "${cfg}/custom_components"
  rm -rf "${cfg}/custom_components/aliyun_bailian_tts"
  cp -r "${tmp}/tts-repo/custom_components/aliyun_bailian_tts" "${cfg}/custom_components/"

  echo "==> 安装 Aliyun BaiLian STT"
  rm -rf "${cfg}/custom_components/aliyun_bailian_stt"
  cp -r "${STT_SRC}" "${cfg}/custom_components/aliyun_bailian_stt"

  echo "==> 完成。配置说明: docs/voice-assistant-setup.md"
  echo "    HA → 添加集成: Aliyun BaiLian STT / Aliyun BaiLian TTS"
  echo "    LLM 单独添加 OpenAI 对话（DeepSeek 或百炼 Qwen）"
}

if [[ -n "${REMOTE}" ]]; then
  echo "==> 打包并部署 TTS+STT → ${REMOTE}"
  tmp="$(mktemp -d)"
  trap 'rm -rf "${tmp}"' EXIT
  git clone --depth 1 "${TTS_REPO}" "${tmp}/tts-repo"
  tar czf /tmp/voice-components.tgz \
    -C "${tmp}/tts-repo/custom_components" aliyun_bailian_tts \
    -C "${STT_SRC}/.." aliyun_bailian_stt
  ssh "${REMOTE}" "sudo mkdir -p ~/硬件-cursor/homeassistant/config/custom_components && sudo rm -rf ~/硬件-cursor/homeassistant/config/custom_components/aliyun_bailian_tts ~/硬件-cursor/homeassistant/config/custom_components/aliyun_bailian_stt"
  scp /tmp/voice-components.tgz "${REMOTE}:/tmp/voice-components.tgz"
  ssh "${REMOTE}" "sudo tar xzf /tmp/voice-components.tgz -C ~/硬件-cursor/homeassistant/config/custom_components && sudo chown -R \$(whoami):\$(whoami) ~/硬件-cursor/homeassistant/config/custom_components/aliyun_bailian_tts ~/硬件-cursor/homeassistant/config/custom_components/aliyun_bailian_stt && rm /tmp/voice-components.tgz && echo '已安装 aliyun_bailian_tts + aliyun_bailian_stt'"
  rm -f /tmp/voice-components.tgz
  echo "==> 请重启 Home Assistant"
else
  install_local "${HA_CONFIG}"
fi
