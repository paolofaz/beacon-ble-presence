"""Config flow for Beacon BLE Presence."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_MAJOR,
    CONF_MINOR,
    CONF_NAME,
    CONF_TIMEOUT,
    CONF_UUID,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MAX_TIMEOUT,
    MIN_TIMEOUT,
)


def _normalize_uuid(value: str) -> str:
    """Normalize a UUID to canonical lower-case form."""
    return str(UUID(value.strip()))


def _entry_unique_id(uuid: str, major: int, minor: int) -> str:
    """Return the stable config-entry identity for an iBeacon."""
    return f"{uuid}_{major}_{minor}"


class BeaconBlePresenceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add one beacon per config entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized_uuid = _normalize_uuid(user_input[CONF_UUID])
            except (ValueError, AttributeError):
                errors[CONF_UUID] = "invalid_uuid"
            else:
                major = user_input[CONF_MAJOR]
                minor = user_input[CONF_MINOR]
                unique_id = _entry_unique_id(normalized_uuid, major, minor)

                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                data = dict(user_input)
                data[CONF_UUID] = normalized_uuid
                return self.async_create_entry(title=data[CONF_NAME], data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): vol.All(
                    str, vol.Strip, vol.Length(min=1, max=64)
                ),
                vol.Required(CONF_UUID): vol.All(str, vol.Strip,
                vol.Required(CONF_MAJOR, default=1): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=65535)
                ),
                vol.Required(CONF_MINOR, default=1): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=65535)
                ),
                vol.Required(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_TIMEOUT, max=MAX_TIMEOUT)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return BeaconBlePresenceOptionsFlow()


class BeaconBlePresenceOptionsFlow(config_entries.OptionsFlow):
    """Allow changing the presence timeout without re-adding the beacon."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(
            CONF_TIMEOUT,
            self.config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_TIMEOUT, default=current): vol.All(
                        vol.Coerce(int), vol.Range(min=MIN_TIMEOUT, max=MAX_TIMEOUT)
                    )
                }
            ),
        )
