# App-open location payload support

This document plans the required `zepp2hass` change for the combined `tt_zepp_app`.

## Goal

`zepp2hass` SHALL accept app-open location snapshots sent by `tt_zepp_app` through the existing sensor sync endpoint.

The location snapshot is measured watch data. It SHALL NOT be treated as subjective Tagestracker input and SHALL NOT write Tagestracker helper entities by default.

## Payload contract

The payload SHOULD contain the normal Zepp2Hass envelope plus a `location` object.

Required envelope fields:

- `id`: stable payload id for retry/idempotency handling
- `schema_version`: payload schema version
- `record_time`: timestamp of the location record
- `source_app`: expected to identify `tt_zepp_app`
- `device`: watch/device identity when available

Required `location` fields:

- `latitude`: WGS-84 latitude
- `longitude`: WGS-84 longitude

Recommended optional `location` fields:

- `record_time`: location-specific timestamp if different from the envelope timestamp
- `status`: Geolocation status used by the watch app
- `source`: for example `app_open_geolocation`
- `coordinate_system`: expected `WGS-84`

## Validation rules

- Reject or ignore location data when `latitude` or `longitude` is missing, non-numeric, zero-by-default, stale, or invalid.
- Ignore unknown location fields defensively.
- Keep processing other sensor categories when the location object is invalid.
- Use the stable `id` to avoid duplicate events/entities where practical.
- Do not log raw coordinates in normal logs unless explicit debug mode is enabled.

## Home Assistant representation

The exact representation can be implemented as one of these measured-data options:

- separate measured sensor entities for latitude/longitude and last update time,
- a Home Assistant event/entity describing the latest app-open location snapshot,
- or device-tracker-style data if that fits the integration architecture.

Whichever representation is chosen, it SHALL be clearly labeled as watch-measured/app-open location data.

## Out of scope

- Writing exact coordinates into Tagestracker helpers by default.
- Inferring mood, energy, pain, relationship state, or intent from location.
- Continuous background location tracking. This contract is only for a snapshot when the user opens the watch app.
