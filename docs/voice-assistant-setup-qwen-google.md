# 语音助手配置：Google STT + 百炼 Qwen TTS

板子 **BOOT 按住说话** → HA 语音流水线 → 扬声器播放。

## 分工

| 环节 | 用什么 | 说明 |
|------|--------|------|
| 录音 | 气候站板子 | 已配置 |
| **语音→文字 STT** | **Google Cloud** | Edge TTS **没有** STT，只能用 Google 等 |
| **对话大脑** | **OpenAI 兼容 + 百炼 Qwen** | 见下文 |
| **文字→语音 TTS** | **Aliyun BaiLian TTS (Qwen3-TTS)** | 已安装 custom component |

---

## 一、百炼 Qwen TTS（文字转语音）

1. 打开 [百炼 API Key](https://bailian.console.aliyun.com/?tab=model#/api-key)，复制 Key
2. HA → **设置 → 设备与服务 → 添加集成**
3. 搜索 **Aliyun BaiLian TTS** → 添加
4. 填入 API Key；选项建议：
   - **Model**：`qwen3-tts-flash`
   - **Voice**：`Cherry`（或列表里任一中文音色）
5. 提交

---

## 二、Google Cloud STT（语音转文字）

Edge TTS 与 Google **不是同一套 STT**；听写必须用 **Google Cloud Speech-to-Text**。

### 2.1 谷歌云准备（一次性）

1. 打开 [Google Cloud Console](https://console.cloud.google.com/)
2. 新建项目 → 启用 **Cloud Speech-to-Text API**
3. **IAM → 服务账号** → 创建 → 角色选 **Cloud Speech 客户端**（或 Editor）
4. 创建 **JSON 密钥**，下载到电脑

### 2.2 导入 HA

1. 把 JSON 文件拷到 Pi：

```bash
scp your-key.json church@192.168.31.155:~/硬件-cursor/homeassistant/config/google_cloud.json
```

2. HA → **设置 → 设备与服务 → 添加集成 → Google Cloud**
3. 上传/选择该 JSON；启用 **Speech-to-text**
4. 语言选 **zh-CN**；若报错可改 STT 模型为 `command_and_search`

（TTS 部分可关掉，朗读用百炼 Qwen 即可。）

---

## 三、Qwen 对话大脑（OpenAI 兼容）

1. HA → **添加集成 → OpenAI**
2. API Key：百炼 DashScope Key（可与 TTS 相同）
3. Base URL：`https://dashscope.aliyuncs.com/compatible-mode/v1`
4. 模型：`qwen-plus` 或 `qwen-turbo`

---

## 四、创建语音助手 pi-voice

**设置 → 语音助手 → 添加助手**：

| 字段 | 选择 |
|------|------|
| 名称 | `pi-voice` |
| 语言 | 中文 |
| 对话代理 | **OpenAI**（百炼 Qwen） |
| 语音转文字 | **Google Cloud** |
| 文字转语音 | **Aliyun BaiLian TTS** |

保存。

---

## 五、分配给气候站板子

**设置 → 设备与服务 → ESPHome → 气候站** → Voice Assistant → 选 **pi-voice**。

---

## 六、测试

1. **按住 BOOT**，说：「西雷丽现在多少度」
2. **松开 BOOT**
3. 等板子用 Qwen 音色播报

---

## 常见问题

- **STT 下拉仍为空**：先完成 Google Cloud 集成并重启 HA
- **TTS 找不到 Aliyun**：重启 HA 后再添加集成
- **Google 在国内不稳定**：可改用 HACS **Groq Whisper Cloud** 作 STT（需 Groq API Key）
