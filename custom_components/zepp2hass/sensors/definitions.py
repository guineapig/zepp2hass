"""Sensor definitions for Zepp2Hass.

This module contains declarative sensor definitions using NamedTuples.
Sensors are configured here rather than in code for easier maintenance.

Two types of definitions:
- SensorDef: Standard sensor reading from a single JSON path
- SensorWithTargetDef: Sensor with current value and target attribute
"""
from __future__ import annotations

from typing import NamedTuple, Final

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfLength,
    UnitOfTime,
)


class SensorDef(NamedTuple):
    """Definition for a standard sensor that reads from a JSON path.

    Attributes:
        json_path: Dot-separated path to value in coordinator data
        key: Unique sensor identifier (used in entity_id)
        name: Human-readable sensor name
        unit: Unit of measurement (e.g., "bpm", "%")
        icon: MDI icon name (e.g., "mdi:heart")
        formatter: Name of formatter function from formatters.py
        category: Entity category (DIAGNOSTIC, CONFIG, or None)
        device_class: Home Assistant device class for special handling
    """

    json_path: str
    key: str
    name: str
    unit: str | None = None
    icon: str | None = None
    formatter: str | None = None
    category: EntityCategory | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    attributes_map: dict[str, str] | None = None


class SensorWithTargetDef(NamedTuple):
    """Definition for a sensor with current value and target attribute.

    Used for sensors like steps, calories where there's a goal/target.

    Attributes:
        current_path: Dot-separated path to current value
        target_path: Dot-separated path to target value
        key: Unique sensor identifier
        name: Human-readable sensor name
        unit: Unit of measurement
        icon: MDI icon name
        formatter: Name of formatter function
        device_class: Home Assistant device class
    """

    current_path: str
    target_path: str
    key: str
    name: str
    unit: str | None = None
    icon: str | None = None
    formatter: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None


# =============================================================================
# SENSOR DEFINITIONS
# =============================================================================
# Organized by category for easier maintenance and readability

# --- Diagnostic Sensors ---
# System information and device status

_DIAGNOSTIC_SENSORS: Final[list[SensorDef]] = [
    SensorDef(
        json_path="record_time",
        key="record_time",
        name="Record Time",
        icon="mdi:calendar-clock",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="last_update",
        key="last_update",
        name="Last Update",
        icon="mdi:update",
        category=EntityCategory.DIAGNOSTIC,
        attributes_map={"record_time": "record_time"},
    ),
    SensorDef(
        json_path="id",
        key="payload_id",
        name="Payload ID",
        icon="mdi:identifier",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="schema_version",
        key="payload_schema_version",
        name="Payload Schema Version",
        icon="mdi:counter",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="kind",
        key="payload_kind",
        name="Payload Kind",
        icon="mdi:shape-outline",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="source_app",
        key="source_app",
        name="Source App",
        icon="mdi:application",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="screen.status",
        key="screen_status",
        name="Screen Status",
        icon="mdi:monitor",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="screen.aod_mode",
        key="screen_aod_mode",
        name="Screen AOD Mode",
        icon="mdi:monitor-eye",
        formatter="format_bool",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="screen.light",
        key="screen_light",
        name="Screen Brightness",
        unit=PERCENTAGE,
        icon="mdi:brightness-6",
        category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="trigger.event",
        key="trigger_event",
        name="Trigger Event",
        icon="mdi:lightning-bolt",
        category=EntityCategory.DIAGNOSTIC,
        attributes_map={"status": "trigger.status"},
    ),
    SensorDef(
        json_path="last_error",
        key="last_error",
        name="Last Error",
        icon="mdi:alert-circle",
        category=EntityCategory.DIAGNOSTIC,
    ),
]

# --- Profile and source identity sensors ---
# The generated entity IDs are stable per Zepp2Hass config entry. These values
# make the current app/profile identity visible for leaderboard mapping.

_PROFILE_SENSORS: Final[list[SensorDef]] = [
    SensorDef(
        json_path="profile.id",
        key="profile_id",
        name="Profile ID",
        icon="mdi:account",
        category=EntityCategory.DIAGNOSTIC,
        attributes_map={"label": "profile.label", "mode": "profile.mode"},
    ),
    SensorDef(
        json_path="profile.label",
        key="profile_label",
        name="Profile Label",
        icon="mdi:account-badge",
        category=EntityCategory.DIAGNOSTIC,
        attributes_map={"id": "profile.id", "mode": "profile.mode"},
    ),
    SensorDef(
        json_path="profile.mode",
        key="profile_mode",
        name="Profile Mode",
        icon="mdi:account-cog",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="profile.movement_upload_enabled",
        key="profile_movement_upload",
        name="Profile Movement Upload",
        icon="mdi:upload",
        formatter="format_bool",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="device.uuid",
        key="source_device_id",
        name="Source Device ID",
        icon="mdi:watch-variant",
        category=EntityCategory.DIAGNOSTIC,
    ),
    SensorDef(
        json_path="device.deviceName",
        key="source_device_name",
        name="Source Device Name",
        icon="mdi:watch",
        category=EntityCategory.DIAGNOSTIC,
    ),
]

# --- Battery Sensor ---
# Device power level

_BATTERY_SENSORS: Final[list[SensorDef]] = [
    SensorDef(
        json_path="battery.current",
        key="battery",
        name="Battery",
        unit=PERCENTAGE,
        icon="mdi:battery",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

# --- Health Sensors ---
# Body measurements and health metrics

_HEALTH_SENSORS: Final[list[SensorDef]] = [
    SensorDef(
        json_path="body_temperature.current.value",
        key="body_temperature",
        name="Body Temperature",
        unit=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        formatter="format_body_temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="stress.current.value",
        key="stress_value",
        name="Stress",
        unit="points",
        icon="mdi:emoticon-sad-outline",
        state_class=SensorStateClass.MEASUREMENT,
        attributes_map={"last_week": "stress.last_week"},
    ),
]

# --- Activity Sensors ---
# Physical activity metrics

_ACTIVITY_SENSORS: Final[list[SensorDef]] = [
    SensorDef(
        json_path="distance.current",
        key="distance",
        name="Distance",
        unit=UnitOfLength.METERS,
        icon="mdi:map-marker-distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
]

# --- Compass Sensors ---
# Direction data from the watch compass sensor

_COMPASS_SENSORS: Final[list[SensorDef]] = [
    SensorDef(
        json_path="compass.direction",
        key="compass_direction",
        name="Compass Direction",
        icon="mdi:compass-outline",
        attributes_map={"calibrated": "compass.status"},
    ),
    SensorDef(
        json_path="compass.direction_angle",
        key="compass_direction_angle",
        name="Compass Direction Angle",
        unit=DEGREE,
        icon="mdi:compass",
        formatter="format_compass_angle",
        state_class=SensorStateClass.MEASUREMENT,
        attributes_map={
            "direction": "compass.direction",
            "calibrated": "compass.status",
        },
    ),
    SensorDef(
        json_path="compass.status",
        key="compass_status",
        name="Compass Calibrated",
        icon="mdi:compass-rose",
        formatter="format_bool",
        category=EntityCategory.DIAGNOSTIC,
    ),
]

# --- Heart Rate Sensors ---
# Heart rate measurements and statistics

_HEART_RATE_SENSORS: Final[list[SensorDef]] = [
    SensorDef(
        json_path="heart_rate.last",
        key="heart_rate_last",
        name="Heart Rate",
        unit="bpm",
        icon="mdi:heart-pulse",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="heart_rate.resting",
        key="heart_rate_resting",
        name="Heart Rate Resting",
        unit="bpm",
        icon="mdi:heart",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="heart_rate.summary.maximum.hr_value",
        key="heart_rate_max",
        name="Heart Rate Max",
        unit="bpm",
        icon="mdi:heart-flash",
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

# --- Sleep Sensors ---
# Sleep tracking data

_SLEEP_SENSORS: Final[list[SensorDef]] = [
    SensorDef(
        json_path="sleep.info.startTime",
        key="sleep_start",
        name="Sleep Start",
        icon="mdi:clock-start",
        formatter="format_sleep_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorDef(
        json_path="sleep.info.endTime",
        key="sleep_end",
        name="Sleep End",
        icon="mdi:clock-end",
        formatter="format_sleep_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorDef(
        json_path="sleep.info.deepTime",
        key="sleep_deep",
        name="Sleep Deep",
        unit=UnitOfTime.MINUTES,
        icon="mdi:weather-night",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="sleep.info.totalTime",
        key="sleep_total",
        name="Sleep Total",
        unit=UnitOfTime.MINUTES,
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

# --- Workout Session Sensors ---
# Live metrics during a workout

_WORKOUT_SESSION_SENSORS: Final[list[SensorDef]] = [
    # State Sensor (derived from one of the metrics, e.g. speed)
    SensorDef(
        json_path="workout_session.speed.parsed",
        key="workout_state",
        name="Workout State",
        icon="mdi:run-fast",
        formatter="format_workout_state",
    ),
    # Metrics
    SensorDef(
        json_path="workout_session.speed.parsed",
        key="workout_speed",
        name="Workout Speed",
        unit="km/h",
        icon="mdi:speedometer",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="workout_session.avg_speed.parsed",
        key="workout_avg_speed",
        name="Workout Avg Speed",
        unit="km/h",
        icon="mdi:speedometer-medium",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="workout_session.pace.parsed",
        key="workout_pace",
        name="Workout Pace",
        unit="min/km",
        icon="mdi:timer-sand",
        formatter="format_session_metric",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="workout_session.avg_pace.parsed",
        key="workout_avg_pace",
        name="Workout Avg Pace",
        unit="min/km",
        icon="mdi:timer-sand",
        formatter="format_session_metric",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="workout_session.distance.parsed",
        key="workout_distance",
        name="Workout Distance",
        unit=UnitOfLength.METERS,
        icon="mdi:map-marker-distance",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDef(
        json_path="workout_session.duration.parsed",
        key="workout_duration",
        name="Workout Duration",
        unit=UnitOfTime.SECONDS,
        icon="mdi:timer-outline",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDef(
        json_path="workout_session.calories.parsed",
        key="workout_calories",
        name="Workout Calories",
        unit="kcal",
        icon="mdi:fire",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDef(
        json_path="workout_session.cadence.parsed",
        key="workout_cadence",
        name="Workout Cadence",
        unit="rpm",
        icon="mdi:run",
        formatter="format_session_metric",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="workout_session.avg_cadence.parsed",
        key="workout_avg_cadence",
        name="Workout Avg Cadence",
        unit="rpm",
        icon="mdi:run",
        formatter="format_session_metric",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="workout_session.altitude.parsed",
        key="workout_altitude",
        name="Workout Altitude",
        unit=UnitOfLength.METERS,
        icon="mdi:image-filter-hdr",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="workout_session.total_up_altitude.parsed",
        key="workout_total_up_altitude",
        name="Workout Total Up Altitude",
        unit=UnitOfLength.METERS,
        icon="mdi:arrow-up-bold",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDef(
        json_path="workout_session.total_count.parsed",
        key="workout_total_count",
        name="Workout Total Count",
        unit="times",
        icon="mdi:counter",
        formatter="format_session_metric",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDef(
        json_path="workout_session.vertical_speed.parsed",
        key="workout_vertical_speed",
        name="Workout Vertical Speed",
        unit="m/h",
        icon="mdi:arrow-up-bold-circle-outline",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        json_path="workout_session.downhill_count.parsed",
        key="workout_downhill_count",
        name="Workout Downhill Count",
        unit="times",
        icon="mdi:arrow-down-bold",
        formatter="format_session_metric",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDef(
        json_path="workout_session.total_downhill_distance.parsed",
        key="workout_total_downhill_distance",
        name="Workout Total Downhill Distance",
        unit=UnitOfLength.METERS,
        icon="mdi:arrow-down-bold-circle-outline",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorDef(
        json_path="workout_session.stride.parsed",
        key="workout_stride",
        name="Workout Stride",
        unit=UnitOfLength.CENTIMETERS,
        icon="mdi:shoe-print",
        formatter="format_session_metric",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
]

# =============================================================================
# COMBINED DEFINITIONS
# =============================================================================

# All standard sensor definitions
SENSOR_DEFINITIONS: Final[list[SensorDef]] = [
    *_DIAGNOSTIC_SENSORS,
    *_PROFILE_SENSORS,
    *_BATTERY_SENSORS,
    *_HEALTH_SENSORS,
    *_ACTIVITY_SENSORS,
    *_COMPASS_SENSORS,
    *_HEART_RATE_SENSORS,
    *_SLEEP_SENSORS,
    *_WORKOUT_SESSION_SENSORS,
]

# =============================================================================
# SENSORS WITH TARGET VALUES
# =============================================================================
# These sensors show current progress toward a daily goal

SENSORS_WITH_TARGET: Final[list[SensorWithTargetDef]] = [
    SensorWithTargetDef(
        current_path="steps.current",
        target_path="steps.target",
        key="steps",
        name="Steps",
        unit="steps",
        icon="mdi:walk",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorWithTargetDef(
        current_path="calorie.current",
        target_path="calorie.target",
        key="calories",
        name="Calories",
        unit="kcal",
        icon="mdi:fire",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorWithTargetDef(
        current_path="fat_burning.current",
        target_path="fat_burning.target",
        key="fat_burning",
        name="Fat Burning",
        unit=UnitOfTime.MINUTES,
        icon="mdi:run-fast",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    SensorWithTargetDef(
        current_path="stands.current",
        target_path="stands.target",
        key="stands",
        name="Stands",
        unit="times",
        icon="mdi:human-handsup",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
]
