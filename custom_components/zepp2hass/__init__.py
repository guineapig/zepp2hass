"""The Zepp2Hass integration.

This integration receives data from Zepp smartwatches via webhooks
and exposes it as Home Assistant sensors.
"""
from __future__ import annotations


import asyncio
import json
import logging
import time
from pathlib import Path

from typing import Any

from aiohttp import web

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.webhook import (
    async_generate_id as webhook_generate_id,
    async_register as webhook_register,
    async_unregister as webhook_unregister,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_WEBHOOK_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.network import get_url

from .const import (
    DOMAIN,
    PLATFORMS,
    DEFAULT_MANUFACTURER,
    DEFAULT_MODEL,
    CONF_BASE_URL,
    LIVE_FINDER_RATE_LIMIT_REQUESTS,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    RECENT_PAYLOAD_ID_LIMIT,
)
from .coordinator import ZeppDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Cache for dashboard HTML template
_DASHBOARD_TEMPLATE: str | None = None

_OBJECT_SECTIONS: frozenset[str] = frozenset(
    {
        "battery",
        "ble",
        "blood_oxygen",
        "body_temperature",
        "calorie",
        "capabilities",
        "compass",
        "device",
        "debug",
        "distance",
        "fat_burning",
        "finder_session",
        "geolocation",
        "geo_location",
        "heart_rate",
        "location",
        "pai",
        "screen",
        "sleep",
        "stands",
        "steps",
        "stress",
        "trigger",
        "user",
        "workout",
        "workout_session",
    }
)

_SCALAR_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "schema_version",
        "record_time",
        "last_update",
        "kind",
        "source_app",
        "created_at",
        "attempt_count",
        "is_wearing",
        "request_correlation_id",
        "sensor_sync_interval_minutes",
    }
)

_KNOWN_PROFILE_IDS: frozenset[str] = frozenset({"sarah", "flo", "zora"})


async def _load_dashboard_template() -> str:
    """Load dashboard HTML template, with caching.
    
    Returns:
        Dashboard HTML template content
    """
    global _DASHBOARD_TEMPLATE
    if _DASHBOARD_TEMPLATE is None:
        dashboard_path = Path(__file__).parent / "frontend" / "dashboard.html"
        try:
            # Use asyncio.to_thread to run the blocking file read in a thread pool
            _DASHBOARD_TEMPLATE = await asyncio.to_thread(dashboard_path.read_text, encoding="utf-8")
        except FileNotFoundError:
            _LOGGER.error("Dashboard template not found at %s", dashboard_path)
            _DASHBOARD_TEMPLATE = "<html><body><h1>Webhook URL</h1><p>{{WEBHOOK_URL}}</p></body></html>"
    return _DASHBOARD_TEMPLATE


def _is_rate_limited(
    entry_data: dict[str, Any],
    request_limit: int = RATE_LIMIT_REQUESTS,
    bucket: str = "request_timestamps",
) -> bool:
    """Return True when the entry exceeded its POST rate window."""
    now = time.monotonic()
    timestamps: list[float] = entry_data.setdefault(bucket, [])
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps[:] = [stamp for stamp in timestamps if stamp >= window_start]

    if len(timestamps) >= request_limit:
        return True

    timestamps.append(now)
    return False


def _get_payload_id(payload: dict[str, Any]) -> str | None:
    """Return the optional idempotency key from a payload."""
    payload_id = payload.get("id")
    if payload_id is None:
        return None
    return str(payload_id).strip() or None


def _is_duplicate_payload(entry_data: dict[str, Any], payload_id: str | None) -> bool:
    """Track recent payload IDs and return True for duplicate submissions."""
    if not payload_id:
        return False

    seen_ids: list[str] = entry_data.setdefault("recent_payload_ids", [])
    if payload_id in seen_ids:
        entry_data["duplicate_payload_count"] = (
            int(entry_data.get("duplicate_payload_count", 0)) + 1
        )
        return True

    seen_ids.append(payload_id)
    if len(seen_ids) > RECENT_PAYLOAD_ID_LIMIT:
        del seen_ids[: len(seen_ids) - RECENT_PAYLOAD_ID_LIMIT]
    return False


def _validate_payload(payload: dict[str, Any]) -> str | None:
    """Validate known Zepp2Hass payload fields without blocking future fields."""
    if not payload:
        return "Payload must not be empty"

    for key in _OBJECT_SECTIONS:
        value = payload.get(key)
        if value is not None and not isinstance(value, dict):
            return f"Field '{key}' must be a JSON object"

    for key in _SCALAR_FIELDS:
        value = payload.get(key)
        if isinstance(value, (dict, list)):
            return f"Field '{key}' must be a scalar value"

    source = payload.get("source")
    if isinstance(source, list):
        return "Field 'source' must be a string or JSON object"

    profile = payload.get("profile")
    if profile is not None:
        message = _validate_profile(profile)
        if message:
            return message

    capabilities = payload.get("capabilities")
    if isinstance(capabilities, dict):
        for key in ("unsupported", "unavailable", "skipped"):
            value = capabilities.get(key)
            if value is not None and not isinstance(value, list):
                return f"Field 'capabilities.{key}' must be a list"

    debug = payload.get("debug")
    if isinstance(debug, dict):
        forbidden_debug_keys = {
            "token",
            "url",
            "request_body",
            "latitude",
            "longitude",
            "coordinates",
            "ble",
            "free_text",
            "medication",
            "relationship",
        }
        for key, value in debug.items():
            if key in forbidden_debug_keys:
                return f"Field 'debug.{key}' is not allowed"
            if isinstance(value, (dict, list)):
                return f"Field 'debug.{key}' must be a scalar value"
            if isinstance(value, str) and len(value) > 128:
                return f"Field 'debug.{key}' exceeds the maximum length"

    for location_key in ("location", "geolocation", "geo_location"):
        location = payload.get(location_key)
        if isinstance(location, dict):
            message = _validate_location(location_key, location)
            if message:
                return message

    compass = payload.get("compass")
    if isinstance(compass, dict):
        angle = compass.get("direction_angle", compass.get("heading"))
        if angle is not None:
            try:
                if not 0 <= float(angle) < 360:
                    return "Field 'compass.direction_angle' must be between 0 and 360"
            except (TypeError, ValueError):
                return "Field 'compass.direction_angle' must be numeric"

    ble = payload.get("ble")
    if isinstance(ble, dict):
        observations = ble.get("observations")
        if observations is not None and not isinstance(observations, list):
            return "Field 'ble.observations' must be a list"
        if isinstance(observations, list) and len(observations) > 50:
            return "Field 'ble.observations' exceeds the maximum of 50"

    return None


def _validate_profile(profile: Any) -> str | None:
    """Validate supported profile identity shapes."""
    if isinstance(profile, str):
        return None
    if not isinstance(profile, dict):
        return "Field 'profile' must be a string or JSON object"

    for key in ("id", "label", "mode"):
        value = profile.get(key)
        if value is not None and not isinstance(value, str):
            return f"Field 'profile.{key}' must be a string"

    profile_id = profile.get("id")
    if isinstance(profile_id, str) and profile_id and profile_id not in _KNOWN_PROFILE_IDS:
        _LOGGER.debug("Received payload for unconfigured profile id %s", profile_id)

    return None


def _validate_location(location_key: str, location: dict[str, Any]) -> str | None:
    """Validate app-open location shape without logging precise coordinates."""
    latitude = location.get("latitude", location.get("lat"))
    longitude = location.get("longitude", location.get("lon", location.get("lng")))

    if latitude is None and longitude is None:
        return None
    if latitude is None or longitude is None:
        return f"Field '{location_key}' must include both latitude and longitude"

    if _coordinate_or_dms_to_float(latitude) is None:
        return f"Field '{location_key}.latitude' must be a valid coordinate"
    if _coordinate_or_dms_to_float(longitude) is None:
        return f"Field '{location_key}.longitude' must be a valid coordinate"

    return None


def _coordinate_or_dms_to_float(value: Any) -> float | None:
    """Return a decimal coordinate from a scalar or Zepp DMS object."""
    if isinstance(value, dict):
        degrees = value.get("degrees")
        if degrees is None:
            return None
        try:
            minutes = float(value.get("minutes", 0))
            seconds = float(value.get("seconds", 0))
            coordinate = float(degrees) + (minutes / 60) + (seconds / 3600)
        except (TypeError, ValueError):
            return None

        direction = str(value.get("direction", "")).upper()
        return -coordinate if direction in {"S", "W"} else coordinate

    try:
        return float(value)
    except (TypeError, ValueError):
        return None





# --- Entry setup/unload ---


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zepp2Hass from a config entry.

    Creates coordinator, registers webhook, and sets up device.

    Args:
        hass: Home Assistant instance
        entry: Config entry being set up

    Returns:
        True if setup successful
    """
    hass.data.setdefault(DOMAIN, {})

    entry_id = entry.entry_id
    device_name = entry.data.get("name", "zepp_device")

    # Get or generate webhook ID (for migration from old config entries)
    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if not webhook_id:
        # Migration: generate webhook_id for existing entries without one
        webhook_id = webhook_generate_id()
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_WEBHOOK_ID: webhook_id},
        )
        _LOGGER.info("Migrated entry %s: generated new webhook_id", entry_id)

    # Migration: move base_url from data to options for existing entries
    if CONF_BASE_URL in entry.data and CONF_BASE_URL not in entry.options:
        new_data = dict(entry.data)
        base_url_value = new_data.pop(CONF_BASE_URL)
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            options={CONF_BASE_URL: base_url_value},
        )
        _LOGGER.info("Migrated entry %s: moved base_url from data to options", entry_id)

    # Build webhook URL
    # Check if user provided a custom base URL in options (or data for old entries)
    custom_base_url = entry.options.get(CONF_BASE_URL, "") or entry.data.get(CONF_BASE_URL, "")

    if custom_base_url:
        # Use custom base URL if provided
        base_url = custom_base_url.rstrip("/")
        webhook_path = f"/api/webhook/{webhook_id}"
        full_webhook_url = f"{base_url}{webhook_path}"
        _LOGGER.info("Using custom base URL for webhook: %s", base_url)
    else:
        # Auto-detect base URL using Home Assistant's network configuration
        try:
            base_url = get_url(hass, allow_internal=True, allow_external=True, prefer_external=True)
        except Exception:
            base_url = None

        if not base_url or "localhost" in base_url:
            # You might want to log a warning or show an error in the config_flow
            # because without a real IP or domain, the watch will never work.
            full_webhook_url = "CONFIGURE_URL_IN_HA_NETWORK_SETTINGS"
        else:
            webhook_path = f"/api/webhook/{webhook_id}"
            full_webhook_url = f"{base_url}{webhook_path}"

    # Initialize components
    coordinator = ZeppDataUpdateCoordinator(hass, entry, device_name)


    # Store entry data
    hass.data[DOMAIN][entry_id] = {
        "coordinator": coordinator,
        "webhook_id": webhook_id,
        "webhook_path": webhook_path,
        "webhook_full_url": full_webhook_url,

    }

    # Register webhook using Home Assistant's native webhook component
    # This provides a secure, random URL that is not guessable
    try:
        webhook_register(
            hass,
            DOMAIN,
            f"Zepp2Hass {device_name}",
            webhook_id,
            _create_webhook_handler(hass, entry_id),
            allowed_methods=["GET", "POST"],
        )
    except ValueError:
        _LOGGER.warning("Webhook %s already registered, unregistering and retrying", webhook_id)
        webhook_unregister(hass, webhook_id)
        webhook_register(
            hass,
            DOMAIN,
            f"Zepp2Hass {device_name}",
            webhook_id,
            _create_webhook_handler(hass, entry_id),
            allowed_methods=["GET", "POST"],
        )

    # Register static path for frontend assets (CSS, etc.)
    # Only register once per domain (check if already registered)
    if "_static_registered" not in hass.data[DOMAIN]:
        frontend_path = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths([
            StaticPathConfig(f"/api/{DOMAIN}/static", str(frontend_path), False),
        ])
        hass.data[DOMAIN]["_static_registered"] = True

    # Register device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry_id,
        identifiers={(DOMAIN, entry_id)},
        manufacturer=DEFAULT_MANUFACTURER,
        model=DEFAULT_MODEL,
        name=device_name,
        configuration_url=full_webhook_url,
    )



    _LOGGER.info("Registered Zepp2Hass webhook for %s at %s", device_name, full_webhook_url)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True



def _create_webhook_handler(hass: HomeAssistant, entry_id: str):
    """Create a webhook handler function for the given entry.

    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID

    Returns:
        Async webhook handler function
    """

    async def handle_webhook(
        hass: HomeAssistant, webhook_id: str, request: web.Request
    ) -> web.Response:
        """Handle incoming webhook requests from Zepp devices.

        Args:
            hass: Home Assistant instance
            webhook_id: The webhook ID that was called
            request: The HTTP request

        Returns:
            JSON response indicating success or error, or HTML for GET requests
        """
        entry_data = hass.data.get(DOMAIN, {}).get(entry_id)
        if not entry_data:
            return web.json_response({"error": "Entry not found"}, status=404)

        # Handle GET requests - serve dashboard for copying webhook URL
        if request.method == "GET":
            webhook_url = entry_data["webhook_full_url"]
            webhook_path = entry_data["webhook_path"]
            static_url = f"/api/{DOMAIN}/static"
            
            # Load and process dashboard HTML template
            dashboard_html = await _load_dashboard_template()
            
            # Replace template variables
            dashboard_html = dashboard_html.replace("{{WEBHOOK_URL}}", webhook_url)
            dashboard_html = dashboard_html.replace("{{WEBHOOK_PATH}}", webhook_path)
            dashboard_html = dashboard_html.replace("{{STATIC_URL}}", static_url)
            
            return web.Response(text=dashboard_html, content_type="text/html")

        # Handle POST requests - process webhook payload

        # Parse JSON payload
        try:
            payload = await request.json()
        except (json.JSONDecodeError, ValueError) as exc:
            _LOGGER.error("Invalid JSON from webhook: %s", exc)
            return web.json_response(
                {"error": "Invalid JSON", "message": str(exc)},
                status=400,
            )

        if not isinstance(payload, dict):
            _LOGGER.error("Payload is not a dictionary: %s", type(payload).__name__)
            return web.json_response(
                {"error": "Invalid payload", "message": "Payload must be a JSON object"},
                status=400,
            )

        request_limit = (
            LIVE_FINDER_RATE_LIMIT_REQUESTS
            if payload.get("kind") == "finder_live_snapshot"
            else RATE_LIMIT_REQUESTS
        )
        rate_limit_bucket = (
            "finder_request_timestamps"
            if payload.get("kind") == "finder_live_snapshot"
            else "request_timestamps"
        )
        if _is_rate_limited(entry_data, request_limit, rate_limit_bucket):
            _LOGGER.warning("Rate limit exceeded for Zepp2Hass entry %s", entry_id)
            return web.json_response(
                {
                    "error": "rate_limited",
                    "message": (
                        f"Maximum {request_limit} requests per "
                        f"{RATE_LIMIT_WINDOW_SECONDS} seconds exceeded"
                    ),
                },
                status=429,
            )

        validation_error = _validate_payload(payload)
        if validation_error:
            _LOGGER.warning(
                "Rejected invalid Zepp2Hass webhook payload for %s: %s",
                entry_id,
                validation_error,
            )
            return web.json_response(
                {"error": "Invalid payload", "message": validation_error},
                status=400,
            )

        payload_id = _get_payload_id(payload)
        if _is_duplicate_payload(entry_data, payload_id):
            _LOGGER.debug("Ignored duplicate Zepp2Hass payload for %s", entry_id)
            return web.json_response({"status": "ok"})

        # Process payload
        coordinator: ZeppDataUpdateCoordinator = entry_data["coordinator"]
        coordinator.async_set_updated_data(payload)

        _LOGGER.debug("Received payload for %s", entry_id)
        return web.json_response({"status": "ok"})

    return handle_webhook


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry being unloaded

    Returns:
        True if unload successful
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Unregister webhook
        entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
        webhook_id = entry_data.get("webhook_id")
        if webhook_id:
            webhook_unregister(hass, webhook_id)

        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("Successfully unloaded Zepp2Hass entry %s", entry.entry_id)

    return unload_ok
