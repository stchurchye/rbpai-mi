"""Config flow for Aliyun BaiLian STT."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ENABLE_ITN,
    CONF_MODEL,
    CONF_NAME,
    CONF_TOKEN,
    DEFAULT_ENABLE_ITN,
    DEFAULT_MODEL,
    DOMAIN,
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_TOKEN): str,
        vol.Optional(CONF_MODEL, default=DEFAULT_MODEL): str,
        vol.Optional(CONF_ENABLE_ITN, default=DEFAULT_ENABLE_ITN): bool,
    }
)


class AliyunBaiLianSTTConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Aliyun BaiLian STT config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_TOKEN):
                errors[CONF_TOKEN] = "invalid_token"
            if not user_input.get(CONF_NAME):
                errors[CONF_NAME] = "invalid_name"

            if not errors:
                await self.async_set_unique_id(user_input[CONF_NAME])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                    options=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=OPTIONS_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return options flow handler."""
        return AliyunBaiLianSTTOptionsFlowHandler(config_entry)


class AliyunBaiLianSTTOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options updates."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_TOKEN):
                errors[CONF_TOKEN] = "invalid_token"
            if not user_input.get(CONF_NAME):
                errors[CONF_NAME] = "invalid_name"

            if not errors:
                current_name = self._config_entry.data.get(
                    CONF_NAME, self._config_entry.title
                )
                if user_input.get(CONF_NAME) != current_name:
                    self.hass.config_entries.async_update_entry(
                        self._config_entry,
                        unique_id=user_input[CONF_NAME],
                        title=user_input[CONF_NAME],
                    )
                return self.async_create_entry(title="", data=user_input)

        current_config = self._config_entry.options or self._config_entry.data.copy()
        if CONF_NAME not in current_config:
            current_config[CONF_NAME] = self._config_entry.title

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, current_config
            ),
            errors=errors,
        )
