"""Dependency-free source contract checks for watch debug snapshots."""
from pathlib import Path


init_source = Path("custom_components/zepp2hass/__init__.py").read_text()
coordinator_source = Path(
    "custom_components/zepp2hass/coordinator.py"
).read_text()
definitions_source = Path(
    "custom_components/zepp2hass/sensors/definitions.py"
).read_text()

assert '"debug"' in init_source
assert "forbidden_debug_keys" in init_source
assert "self._latest_debug_data" in coordinator_source
assert "if isinstance(debug_data, dict):" in coordinator_source
assert 'json_path="debug.bridge_state"' in definitions_source
assert 'json_path="debug.pending_request_count"' in definitions_source
assert 'json_path="debug.last_command_status"' in definitions_source

print("watch debug contract harness ok")
