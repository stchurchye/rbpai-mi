DOMAIN = "aliyun_bailian_stt"
CONF_TOKEN = "token"
CONF_MODEL = "model"
CONF_NAME = "name"
CONF_ENABLE_ITN = "enable_itn"

DEFAULT_MODEL = "qwen3-asr-flash"
DEFAULT_ENABLE_ITN = False

SUPPORTED_LANGUAGES = [
    "zh",
    "zh-cn",
    "zh-tw",
    "zh-hk",
    "en",
    "en-us",
    "en-gb",
    "ja",
    "ko",
    "de",
    "fr",
    "es",
    "it",
    "pt",
    "ru",
]

LANGUAGE_TO_ASR = {
    "zh-cn": "zh",
    "zh-tw": "zh",
    "zh-hk": "zh",
    "zh-hans": "zh",
    "zh-hant": "zh",
    "en-us": "en",
    "en-gb": "en",
}
