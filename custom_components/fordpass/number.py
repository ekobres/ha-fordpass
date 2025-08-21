"""Fordpass Switch Entities"""
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import UnitOfTemperature, EVENT_CORE_CONFIG_UPDATE

from custom_components.fordpass import FordPassEntity, RCC_TAGS, FordPassDataUpdateCoordinator
from custom_components.fordpass.const import DOMAIN, COORDINATOR_KEY, REMOTE_START_STATE_ACTIVE
from custom_components.fordpass.const_tags import SWITCHES, Tag, NUMBERS, ExtNumberEntityDescription
from custom_components.fordpass.fordpass_handler import UNSUPPORTED

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Switch from the config."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR_KEY]
    _LOGGER.debug(f"{coordinator.vli}NUMBER async_setup_entry")
    entities = []
    for a_entity_description in NUMBERS:
        a_entity_description: ExtNumberEntityDescription

        if coordinator.tag_not_supported_by_vehicle(a_entity_description.tag):
            _LOGGER.debug(f"{coordinator.vli}NUMBER '{a_entity_description.tag}' not supported for this engine-type/vehicle")
            continue

        entity = FordPassNumber(coordinator, a_entity_description)
        entities.append(entity)

    async_add_entities(entities, True)


class FordPassNumber(FordPassEntity, NumberEntity):
    """Define the Switch for turning ignition off/on"""

    def __init__(self, coordinator: FordPassDataUpdateCoordinator, entity_description: ExtNumberEntityDescription):
        super().__init__(a_tag=entity_description.tag, coordinator=coordinator, description=entity_description)
        self._unsub_config_listener = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if getattr(self, "_tag", None) == Tag.RCC_TEMPERATURE:
            def _on_core_config_update(_):
                self.async_write_ha_state()
            self._unsub_config_listener = self.hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, _on_core_config_update)

    async def async_will_remove_from_hass(self):
        if self._unsub_config_listener:
            self._unsub_config_listener()
            self._unsub_config_listener = None
        await super().async_will_remove_from_hass()

    @property
    def extra_state_attributes(self):
        """Return sensor attributes"""
        return self._tag.get_attributes(self.coordinator.data, self.coordinator.units)

    @property
    def native_value(self):
        """Return Native Value"""
        try:
            value = self._tag.get_state(self.coordinator.data)
            if value is not None and str(value) != UNSUPPORTED:
                return value

        except ValueError:
            _LOGGER.debug(f"{self.coordinator.vli}NUMBER '{self._tag}' get_state failed with ValueError")

        return None

    async def async_set_native_value(self, value) -> None:
        try:
            if value is None or str(value) == "null" or str(value).lower() == "none":
                return
            else:
                await self._tag.async_set_value(self.coordinator.data, self.coordinator.bridge, str(value))

        except ValueError:
            return None

    @property
    def available(self):
        """Return True if entity is available."""
        state = super().available
        if self._tag in RCC_TAGS:
            return state #and Tag.REMOTE_START_STATUS.get_state(self.coordinator.data) == REMOTE_START_STATE_ACTIVE
        return state

    @property
    def suggested_display_precision(self):
        if getattr(self, "_tag", None) == Tag.RCC_TEMPERATURE:
            return 0 if self.hass.config.units.temperature_unit == UnitOfTemperature.FAHRENHEIT else 1
        return super().suggested_display_precision
