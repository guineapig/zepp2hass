"""Human-readable watch location sensor."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import ZeppSensorBase
from .formatters import get_nested_value

if TYPE_CHECKING:
    from ..coordinator import ZeppDataUpdateCoordinator


_LATITUDE_PATHS = (
    "location.latitude",
    "geolocation.latitude",
    "geo_location.latitude",
    "latitude",
)
_LONGITUDE_PATHS = (
    "location.longitude",
    "geolocation.longitude",
    "geo_location.longitude",
    "longitude",
)


class LocationCoordinatesSensor(ZeppSensorBase):
    """Expose coordinates as a regular HA sensor instead of distance."""

    def __init__(self, coordinator: ZeppDataUpdateCoordinator) -> None:
        """Initialize the location coordinates sensor."""
        super().__init__(
            coordinator=coordinator,
            key="location_coordinates",
            name="Location Coordinates",
            icon="mdi:crosshairs-gps",
        )

    @property
    def available(self) -> bool:
        """Return whether valid coordinates are available."""
        return (
            self._is_coordinator_ready()
            and self._coordinate(_LATITUDE_PATHS) is not None
            and self._coordinate(_LONGITUDE_PATHS) is not None
        )

    @property
    def native_value(self) -> str | None:
        """Return readable decimal coordinates."""
        latitude = self._coordinate(_LATITUDE_PATHS)
        longitude = self._coordinate(_LONGITUDE_PATHS)
        if latitude is None or longitude is None:
            return None
        return f"{latitude:.5f}, {longitude:.5f}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return location and heading details for dashboards."""
        attributes = {
            "latitude": self._coordinate(_LATITUDE_PATHS),
            "longitude": self._coordinate(_LONGITUDE_PATHS),
            "record_time": self._first(
                (
                    "location.record_time",
                    "geolocation.record_time",
                    "geo_location.record_time",
                    "record_time",
                )
            ),
            "heading": self._first(("compass.direction_angle",)),
            "direction": self._first(("compass.direction",)),
            "heading_calibrated": self._first(("compass.status",)),
            "accuracy": self._first(
                (
                    "location.accuracy",
                    "geolocation.accuracy",
                    "geo_location.accuracy",
                )
            ),
            "gnss": self._first(
                ("location.gnss", "geolocation.gnss", "geo_location.gnss")
            ),
        }
        return {key: value for key, value in attributes.items() if value is not None}

    def _first(self, paths: tuple[str, ...]) -> Any:
        if not self._data:
            return None
        for path in paths:
            value, found = get_nested_value(self._data, path)
            if found:
                return value
        return None

    def _coordinate(self, paths: tuple[str, ...]) -> float | None:
        value = self._first(paths)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
