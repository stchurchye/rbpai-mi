"""Aliyun BaiLian STT platform using SpeechToTextEntity."""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import wave
from collections.abc import AsyncIterable

import dashscope
from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENABLE_ITN,
    CONF_MODEL,
    CONF_NAME,
    CONF_TOKEN,
    LANGUAGE_TO_ASR,
    SUPPORTED_LANGUAGES,
)

_LOGGER = logging.getLogger(__name__)

DASHSCOPE_BEIJING_API = "https://dashscope.aliyuncs.com/api/v1"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aliyun BaiLian STT entity."""
    options = config_entry.options or config_entry.data
    async_add_entities(
        [
            AliyunBaiLianSTTEntity(
                api_key=options[CONF_TOKEN],
                model=options.get(CONF_MODEL, "qwen3-asr-flash"),
                enable_itn=options.get(CONF_ENABLE_ITN, False),
                name=options.get(CONF_NAME, config_entry.title),
                unique_id=config_entry.entry_id,
            )
        ]
    )


def _extract_transcription(response) -> str:
    """Parse DashScope MultiModalConversation response."""
    try:
        choice = response.output.choices[0]
        content = choice.message.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if text:
                        parts.append(str(text))
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts).strip()
    except (AttributeError, IndexError, KeyError, TypeError) as err:
        _LOGGER.debug("Failed to parse STT response: %s", err)
    return ""


class AliyunBaiLianSTTEntity(SpeechToTextEntity):
    """Aliyun BaiLian Qwen ASR speech-to-text entity."""

    def __init__(
        self,
        api_key: str,
        model: str,
        enable_itn: bool,
        name: str,
        unique_id: str,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._enable_itn = enable_itn
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def supported_languages(self) -> list[str]:
        return SUPPORTED_LANGUAGES

    @property
    def supported_formats(self) -> list[AudioFormats]:
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        return [
            AudioBitRates.BITRATE_8,
            AudioBitRates.BITRATE_16,
            AudioBitRates.BITRATE_24,
            AudioBitRates.BITRATE_32,
        ]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        return [
            AudioSampleRates.SAMPLERATE_8000,
            AudioSampleRates.SAMPLERATE_16000,
            AudioSampleRates.SAMPLERATE_44100,
            AudioSampleRates.SAMPLERATE_48000,
        ]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        return [AudioChannels.CHANNEL_MONO, AudioChannels.CHANNEL_STEREO]

    def _transcribe_wav(self, wav_bytes: bytes, language: str | None) -> str:
        dashscope.base_http_api_url = DASHSCOPE_BEIJING_API
        dashscope.api_key = self._api_key

        data_uri = (
            "data:audio/wav;base64," + base64.b64encode(wav_bytes).decode("ascii")
        )
        messages = [{"role": "user", "content": [{"audio": data_uri}]}]

        asr_options: dict = {"enable_itn": self._enable_itn}
        if language:
            asr_options["language"] = language

        response = dashscope.MultiModalConversation.call(
            model=self._model,
            messages=messages,
            result_format="message",
            asr_options=asr_options,
        )

        if getattr(response, "status_code", None) not in (None, 200):
            message = getattr(response, "message", response)
            raise RuntimeError(f"DashScope STT failed: {message}")

        text = _extract_transcription(response)
        if not text:
            raise RuntimeError(f"Empty STT result: {response}")
        return text

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        """Send recorded audio to Bailian Qwen ASR."""
        data = b""
        async for chunk in stream:
            data += chunk
            if len(data) > 9 * 1024 * 1024:
                _LOGGER.error("Audio exceeds Bailian STT size limit (~10 MB)")
                return SpeechResult("", SpeechResultState.ERROR)

        if not data:
            _LOGGER.error("No audio data received")
            return SpeechResult("", SpeechResultState.ERROR)

        temp_file = io.BytesIO()
        with wave.open(temp_file, "wb") as wav_file:
            wav_file.setnchannels(metadata.channel)
            wav_file.setframerate(metadata.sample_rate)
            wav_file.setsampwidth(2)
            wav_file.writeframes(data)
        wav_bytes = temp_file.getvalue()

        language = metadata.language.lower() if metadata.language else None
        if language:
            language = LANGUAGE_TO_ASR.get(language, language.split("-")[0])

        try:
            text = await asyncio.to_thread(
                self._transcribe_wav, wav_bytes, language
            )
            _LOGGER.debug("Bailian STT transcription: %s", text)
            return SpeechResult(text, SpeechResultState.SUCCESS)
        except Exception as err:
            _LOGGER.error("Bailian STT error: %s", err)
            return SpeechResult("", SpeechResultState.ERROR)
