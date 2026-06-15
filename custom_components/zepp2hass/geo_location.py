"""Geolocation platform for Zepp2Hass.

Exposes the latest pushed watch coordinates as a Home Assistant geo_location
entity so they can be shown on maps and used by geo_location triggers.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from homeassistant.components.geo_location import (
    ATTR_SOURCE,
    GeolocationEvent,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.location import distance

from .const import DOMAIN
from .sensors.formatters import get_nested_value

if TYPE_CHECKING:
    from .coordinator import ZeppDataUpdateCoordinator


_LATITUDE_PATHS: tuple[str, ...] = (
    "geolocation.latitude",
    "geolocation.lat",
    "geo_location.latitude",
    "geo_location.lat",
    "location.latitude",
    "location.lat",
    "latitude",
)

_LONGITUDE_PATHS: tuple[str, ...] = (
    "geolocation.longitude",
    "geolocation.lon",
    "geolocation.lng",
    "geo_location.longitude",
    "geo_location.lon",
    "geo_location.lng",
    "location.longitude",
    "location.lon",
    "location.lng",
    "longitude",
)

_STATUS_PATHS: tuple[str, ...] = (
    "geolocation.status",
    "geo_location.status",
    "location.status",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Zepp2Hass geolocation platform."""
    coordinator: ZeppDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][
        "coordinator"
    ]

    async_add_entities([ZeppGeolocationEvent(coordinator)])


class ZeppGeolocationEvent(
    CoordinatorEntity["ZeppDataUpdateCoordinator"],
    GeolocationEvent,
):
    """Latest geolocation reported by the Zepp watch."""

    _attr_should_poll = False
    _attr_source = DOMAIN
    _attr_unit_of_measurement = UnitOfLength.METERS
    _attr_icon = "mdi:map-marker"

    def __init__(self, coordinator: ZeppDataUpdateCoordinator) -> None:
        """Initialize the geolocation entity."""
        super().__init__(coordinator)
        self._attr_name = f"{coordinator.device_name} Location"
        self._attr_unique_id = f"{DOMAIN}_{coordinator.entry_id}_geolocation"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True when valid coordinates are available."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return False

        status = self._status
        if isinstance(status, str) and status.upper() == "V":
            return False

        return self.latitude is not None and self.longitude is not None

    @property
    def latitude(self) -> float | None:
        """Return latitude in WGS-84 decimal degrees."""
        return self._coordinate_from_paths(_LATITUDE_PATHS)

    @property
    def longitude(self) -> float | None:
        """Return longitude in WGS-84 decimal degrees."""
        return self._coordinate_from_paths(_LONGITUDE_PATHS)

    @property
    def distance(self) -> float | None:
        """Return distance from Home Assistant's configured home location."""
        latitude = self.latitude
        longitude = self.longitude
        if latitude is None or longitude is None:
            return None

        return distance(
            self.hass.config.latitude,
            self.hass.config.longitude,
            latitude,
            longitude,
        )

    @property
    def state_attributes(self) -> dict[str, Any]:
        """Return state attributes for the geolocation entity."""
        data: dict[str, Any] = {ATTR_SOURCE: self.source}

        if self.latitude is not None:
            data[ATTR_LATITUDE] = round(self.latitude, 5)
        if self.longitude is not None:
            data[ATTR_LONGITUDE] = round(self.longitude, 5)

        optional_attributes = {
            "record_time": self._first_value(
                (
                    "location.record_time",
                    "geolocation.record_time",
                    "geo_location.record_time",
                    "record_time",
                )
            ),
            "kind": self._first_value(("kind",)),
            "source_app": self._first_value(("source_app", "source.app")),
            "profile_id": self._first_value(("profile.id",)),
            "profile_label": self._first_value(("profile.label",)),
            "status": self._status,
            "altitude": self._first_value(
                (
                    "geolocation.altitude",
                    "geo_location.altitude",
                    "location.altitude",
                    "altitude",
                )
            ),
            "accuracy": self._first_value(
                (
                    "geolocation.accuracy",
                    "geo_location.accuracy",
                    "location.accuracy",
                    "accuracy",
                )
            ),
            "speed": self._first_value(
                (
                    "geolocation.speed",
                    "geo_location.speed",
                    "location.speed",
                )
            ),
            "setting": self._first_value(
                (
                    "geolocation.setting",
                    "geo_location.setting",
                    "location.setting",
                )
            ),
            "gnss": self._first_value(
                (
                    "geolocation.gnss",
                    "geo_location.gnss",
                    "location.gnss",
                )
            ),
        }

        data.update(
            {
                key: value
                for key, value in optional_attributes.items()
                if value is not None
            }
        )
        return data

    @property
    def _status(self) -> Any:
        """Return geolocation status from the payload, if present."""
        return self._first_value(_STATUS_PATHS)

    def _first_value(self, paths: tuple[str, ...]) -> Any:
        """Return the first found value from a list of payload paths."""
        if not self.coordinator.data:
            return None

        for path in paths:
            value, found = get_nested_value(self.coordinator.data, path)
            if found:
                return value
        return None

    def _coordinate_from_paths(self, paths: tuple[str, ...]) -> float | None:
        """Return a decimal coordinate from the first matching payload path."""
        return _coordinate_to_float(self._first_value(paths))


def _coordinate_to_float(value: Any) -> float | None:
    """Convert Zepp DD or DMS coordinate values to decimal degrees."""
    if value is None:
        return None

    if isinstance(value, dict):
        direction = str(value.get("direction", "")).upper()
        degrees = value.get("degrees")
        minutes = value.get("minutes", 0)
        seconds = value.get("seconds", 0)
        if degrees is None:
            return None

        try:
            coordinate = (
                float(degrees)
                + (float(minutes) / 60)
                + (float(seconds) / 3600)
            )
        except (TypeError, ValueError):
            return None

        if direction in {"S", "W"}:
            coordinate *= -1
        return coordinate

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
