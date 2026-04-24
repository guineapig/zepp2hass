"""Raw data sensor for Zepp2Hass.

Exposes the entire JSON payload for debugging and advanced templating.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from homeassistant.helpers.entity import EntityCategory

from .base import ZeppSensorBase

if TYPE_CHECKING:
    from ..coordinator import ZeppDataUpdateCoordinator


class RawDataSensor(ZeppSensorBase):
    """Sensor that exposes the full raw payload as attributes."""

    def __init__(self, coordinator: ZeppDataUpdateCoordinator) -> None:
        """Initialize the raw data sensor."""
        super().__init__(
            coordinator=coordinator,
            key="raw_data",
            name="Raw Data",
            icon="mdi:code-json",
        )
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._is_coordinator_ready()

    @property
    def native_value(self) -> str | None:
        """Return the state (record time or just OK)."""
        if not self._is_coordinator_ready():
            return None
        return self._data.get("record_time", "Received") if self._data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the entire raw payload as a single attribute."""
        if not self._data:
            return {}
        # We wrap the entire payload inside 'raw_payload'
        return {"raw_payload": self._data}
