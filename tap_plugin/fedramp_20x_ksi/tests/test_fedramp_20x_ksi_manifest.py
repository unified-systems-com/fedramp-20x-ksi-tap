"""Validation tests for the FedRAMP 20x KSI plugin.

Structure-level tests only in v0 — the plugin is not yet registered in
INSTALLED_APPS, so loads/runs-level validation is deferred until integration.
"""

from pathlib import Path

import pytest

from tap.plugin_testing import find_plugin_source_root
from tap_plugins.validate.service import validate_plugin

PLUGIN_ROOT = find_plugin_source_root(__file__)

pytestmark = pytest.mark.skipif(
    PLUGIN_ROOT is None,
    reason="source-layout validation needs the plugin source tree; installed as a wheel here (delegated to the plugin repo's own build).",
)


class TestFedramp20xKsiStructure:
    def test_structure_passes(self):
        result = validate_plugin(PLUGIN_ROOT, level="structure")
        assert result.ok, result.to_human()

    def test_strict_structure_passes(self):
        result = validate_plugin(PLUGIN_ROOT, level="structure", strict=True)
        assert result.ok, result.to_human()


class TestKsiSchedule:
    """req-fedramp-20x-ksi-collector-schedule-1..3."""

    def _bundle(self):
        import json

        path = PLUGIN_ROOT / "tap_plugin" / "fedramp_20x_ksi" / "grift" / "ksi-schedule.grift.json"
        return json.loads(path.read_text())

    def test_runs_hourly(self):
        node = self._bundle()["batches"][0]["nodes"][0]["node"]
        minute, *rest = node["cron_expression"].split()
        assert minute.isdigit() and rest == ["*", "*", "*", "*"]

    def test_no_overlap(self):
        assert self._bundle()["batches"][0]["nodes"][0]["node"]["max_active_runs"] == 1

    def test_batch_id_bumped_schedule_id_kept(self):
        batch = self._bundle()["batches"][0]
        assert batch["batch_entity"]["entity_id"] != "019e26e8-7cc2-764a-9b66-5961337dd149"
        assert batch["nodes"][0]["entity"]["entity_id"] == "019e26e8-7cc2-764a-9b66-5962d4cd873d"


def test_the_schedule_targets_the_seeded_configuration() -> None:
    """A schedule targets a run configuration, never a collector (req-tap-cares-runconfig-selection-1)."""
    import json

    grift = Path(__file__).resolve().parents[1] / "grift"
    (batch,) = json.loads((grift / "run-configuration.grift.json").read_text())["batches"]
    (configuration,) = batch["nodes"]
    (configures,) = batch["edges"]
    assert configuration["node"]["configurability"] == "not_configurable" and configuration["node"]["settings"] == {}
    assert configures["edge"]["to_key"]["key"] == {"collector_registry": "fedramp_20x_ksi:ksi-catalog"}
    (schedule,) = json.loads((grift / "ksi-schedule.grift.json").read_text())["batches"]
    (target,) = [e["edge"] for e in schedule["edges"] if e["edge"]["edge_type"] == "SCHEDULED_TARGET"]
    assert target["to_entity_id"] == configuration["entity"]["entity_id"]
