# HA-requested finder snapshot payload

Finder snapshots use the normal Zepp2Hass measured-data webhook. They never use
the subjective Tagestracker write-intent endpoint.

```json
{
  "id": "stable-retry-id",
  "schema_version": 2,
  "kind": "ha_requested_location_snapshot",
  "source_app": "tt_zepp_app",
  "record_time": "2026-06-17T20:00:00Z",
  "request_correlation_id": "req-finder-123",
  "profile": {"id": "flo", "label": "Flo", "mode": "full_tracker"},
  "device": {"uuid": "stable-source-device-id"},
  "location": {
    "latitude": 0,
    "longitude": 0,
    "accuracy": 20,
    "record_time": "2026-06-17T20:00:00Z"
  },
  "compass": {"direction_angle": 120, "status": true},
  "ble": {"proximity": "near", "observation_count": 2}
}
```

Rules:

- `request_correlation_id` correlates the measured result with an HA request.
- Duplicate payload `id` values remain successful no-ops.
- Location freshness comes from `location.record_time` or envelope
  `record_time`; missing values are not treated as fresh.
- BLE is coarse (`immediate`, `near`, `far`, `unknown`) and must not claim
  exact distance.
- Raw coordinates and precise BLE identifiers are redacted from diagnostics.
- Config-entry identity remains the stable Zepp2Hass device identity; the
  payload `device.uuid` is exposed only as a diagnostic mapping hint for the
  Home Assistant stable watch-device assignment.
