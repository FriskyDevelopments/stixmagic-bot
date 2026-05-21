"""
Tests for pipeline/motion_presets/__init__.py

Covers the MotionPreset dataclass (moved inline from preset.py), BUILTIN_PRESETS,
PRESET_REGISTRY, get_preset(), and list_presets() introduced/rewritten in this PR.

Note on catalog.py:  The __init__.py try/except at the bottom attempts to import
`list_presets` from .catalog, which would override the filter-capable version added
by this PR.  To test the PR's own list_presets we block that import at the top of
this module so the try/except falls through to the except-ImportError branch.
"""

import sys
import unittest

# Block catalog.py from overriding __init__.py's filter-capable list_presets.
# Setting sys.modules entry to None causes `from .catalog import ...` to raise
# ImportError, which the try/except in __init__.py silently ignores.
sys.modules.setdefault("pipeline.motion_presets.catalog", None)

# Also block preset.py to ensure we are testing the inline MotionPreset, not the
# legacy one from preset.py (which uses duration_ms / description field names).
sys.modules.setdefault("pipeline.motion_presets.preset", None)

from pipeline.motion_presets import (  # noqa: E402
    BUILTIN_PRESETS,
    PRESET_REGISTRY,
    MotionPreset,
    get_preset,
    list_presets,
)


class TestMotionPresetDataclass(unittest.TestCase):
    """Tests for the MotionPreset dataclass itself."""

    def test_required_fields_only(self):
        preset = MotionPreset(id="foo", name="Foo")
        self.assertEqual(preset.id, "foo")
        self.assertEqual(preset.name, "Foo")

    def test_default_loopable_true(self):
        preset = MotionPreset(id="x", name="X")
        self.assertTrue(preset.loopable)

    def test_default_duration_2_0(self):
        preset = MotionPreset(id="x", name="X")
        self.assertEqual(preset.duration, 2.0)

    def test_default_alpha_safe_true(self):
        preset = MotionPreset(id="x", name="X")
        self.assertTrue(preset.alpha_safe)

    def test_default_overlay_safe_true(self):
        preset = MotionPreset(id="x", name="X")
        self.assertTrue(preset.overlay_safe)

    def test_default_sticker_safe_true(self):
        preset = MotionPreset(id="x", name="X")
        self.assertTrue(preset.sticker_safe)

    def test_default_recommended_categories_empty_list(self):
        preset = MotionPreset(id="x", name="X")
        self.assertEqual(preset.recommended_categories, [])

    def test_default_parameter_schema_empty_dict(self):
        preset = MotionPreset(id="x", name="X")
        self.assertEqual(preset.parameter_schema, {})

    def test_default_notes_empty_string(self):
        preset = MotionPreset(id="x", name="X")
        self.assertEqual(preset.notes, "")

    def test_mutable_defaults_are_independent(self):
        """Each instance must get its own list/dict, not a shared one."""
        a = MotionPreset(id="a", name="A")
        b = MotionPreset(id="b", name="B")
        a.recommended_categories.append("letter")
        self.assertEqual(b.recommended_categories, [])

    def test_mutable_parameter_schema_independent(self):
        a = MotionPreset(id="a", name="A")
        b = MotionPreset(id="b", name="B")
        a.parameter_schema["key"] = "val"
        self.assertEqual(b.parameter_schema, {})

    def test_custom_values_stored_correctly(self):
        preset = MotionPreset(
            id="custom",
            name="Custom",
            loopable=False,
            duration=3.5,
            alpha_safe=False,
            overlay_safe=False,
            sticker_safe=False,
            recommended_categories=["icon", "emoji"],
            parameter_schema={"speed": {"type": "float", "default": 1.0}},
            notes="A custom preset",
        )
        self.assertEqual(preset.id, "custom")
        self.assertEqual(preset.name, "Custom")
        self.assertFalse(preset.loopable)
        self.assertEqual(preset.duration, 3.5)
        self.assertFalse(preset.alpha_safe)
        self.assertFalse(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertListEqual(preset.recommended_categories, ["icon", "emoji"])
        self.assertDictEqual(
            preset.parameter_schema, {"speed": {"type": "float", "default": 1.0}}
        )
        self.assertEqual(preset.notes, "A custom preset")


class TestMotionPresetToDict(unittest.TestCase):
    """Tests for MotionPreset.to_dict()."""

    def test_to_dict_contains_all_keys(self):
        preset = MotionPreset(id="p", name="P")
        d = preset.to_dict()
        expected_keys = {
            "id", "name", "loopable", "duration", "alpha_safe",
            "overlay_safe", "sticker_safe", "recommended_categories",
            "parameter_schema", "notes",
        }
        self.assertEqual(set(d.keys()), expected_keys)

    def test_to_dict_values_match_attributes(self):
        preset = MotionPreset(
            id="glitch",
            name="Glitch",
            loopable=True,
            duration=2.0,
            alpha_safe=False,
            overlay_safe=True,
            sticker_safe=True,
            recommended_categories=["letter"],
            parameter_schema={"intensity": {"type": "float", "default": 0.6}},
            notes="Some notes",
        )
        d = preset.to_dict()
        self.assertEqual(d["id"], "glitch")
        self.assertEqual(d["name"], "Glitch")
        self.assertTrue(d["loopable"])
        self.assertEqual(d["duration"], 2.0)
        self.assertFalse(d["alpha_safe"])
        self.assertTrue(d["overlay_safe"])
        self.assertTrue(d["sticker_safe"])
        self.assertListEqual(d["recommended_categories"], ["letter"])
        self.assertDictEqual(
            d["parameter_schema"],
            {"intensity": {"type": "float", "default": 0.6}},
        )
        self.assertEqual(d["notes"], "Some notes")

    def test_to_dict_with_defaults(self):
        preset = MotionPreset(id="simple", name="Simple")
        d = preset.to_dict()
        self.assertTrue(d["loopable"])
        self.assertEqual(d["duration"], 2.0)
        self.assertTrue(d["alpha_safe"])
        self.assertTrue(d["overlay_safe"])
        self.assertTrue(d["sticker_safe"])
        self.assertEqual(d["recommended_categories"], [])
        self.assertEqual(d["parameter_schema"], {})
        self.assertEqual(d["notes"], "")

    def test_to_dict_returns_new_dict_each_call(self):
        preset = MotionPreset(id="p", name="P")
        d1 = preset.to_dict()
        d2 = preset.to_dict()
        self.assertIsNot(d1, d2)

    def test_to_dict_does_not_contain_duration_ms(self):
        """The new dataclass uses 'duration', not the old 'duration_ms' key."""
        preset = MotionPreset(id="p", name="P")
        d = preset.to_dict()
        self.assertNotIn("duration_ms", d)
        self.assertIn("duration", d)


class TestMotionPresetFromDict(unittest.TestCase):
    """Tests for MotionPreset.from_dict()."""

    def test_from_dict_required_fields(self):
        data = {"id": "bounce", "name": "Bounce"}
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "bounce")
        self.assertEqual(preset.name, "Bounce")

    def test_from_dict_defaults_when_optional_missing(self):
        data = {"id": "test", "name": "Test"}
        preset = MotionPreset.from_dict(data)
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration, 2.0)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertTrue(preset.sticker_safe)
        self.assertEqual(preset.recommended_categories, [])
        self.assertEqual(preset.parameter_schema, {})
        self.assertEqual(preset.notes, "")

    def test_from_dict_all_fields_populated(self):
        data = {
            "id": "orbit",
            "name": "Orbit",
            "loopable": True,
            "duration": 3.0,
            "alpha_safe": True,
            "overlay_safe": True,
            "sticker_safe": False,
            "recommended_categories": ["particle", "symbol"],
            "parameter_schema": {"radius": {"type": "integer", "default": 30}},
            "notes": "Orbiting elements.",
        }
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.id, "orbit")
        self.assertEqual(preset.name, "Orbit")
        self.assertTrue(preset.loopable)
        self.assertEqual(preset.duration, 3.0)
        self.assertTrue(preset.alpha_safe)
        self.assertTrue(preset.overlay_safe)
        self.assertFalse(preset.sticker_safe)
        self.assertListEqual(preset.recommended_categories, ["particle", "symbol"])
        self.assertDictEqual(
            preset.parameter_schema, {"radius": {"type": "integer", "default": 30}}
        )
        self.assertEqual(preset.notes, "Orbiting elements.")

    def test_from_dict_override_loopable_false(self):
        data = {"id": "burst", "name": "Burst", "loopable": False}
        preset = MotionPreset.from_dict(data)
        self.assertFalse(preset.loopable)

    def test_from_dict_override_alpha_safe_false(self):
        data = {"id": "g", "name": "G", "alpha_safe": False}
        preset = MotionPreset.from_dict(data)
        self.assertFalse(preset.alpha_safe)

    def test_from_dict_override_sticker_safe_false(self):
        data = {"id": "g", "name": "G", "sticker_safe": False}
        preset = MotionPreset.from_dict(data)
        self.assertFalse(preset.sticker_safe)

    def test_from_dict_notes_field(self):
        data = {"id": "g", "name": "G", "notes": "Special effect."}
        preset = MotionPreset.from_dict(data)
        self.assertEqual(preset.notes, "Special effect.")

    def test_roundtrip_to_dict_from_dict(self):
        """to_dict then from_dict must produce an equal object."""
        original = MotionPreset(
            id="sparkle",
            name="Sparkle",
            loopable=True,
            duration=2.5,
            alpha_safe=True,
            overlay_safe=True,
            sticker_safe=True,
            recommended_categories=["symbol", "frame"],
            parameter_schema={"num_particles": {"type": "integer", "default": 8}},
            notes="Star particles.",
        )
        restored = MotionPreset.from_dict(original.to_dict())
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.loopable, original.loopable)
        self.assertEqual(restored.duration, original.duration)
        self.assertEqual(restored.alpha_safe, original.alpha_safe)
        self.assertEqual(restored.overlay_safe, original.overlay_safe)
        self.assertEqual(restored.sticker_safe, original.sticker_safe)
        self.assertListEqual(restored.recommended_categories, original.recommended_categories)
        self.assertDictEqual(restored.parameter_schema, original.parameter_schema)
        self.assertEqual(restored.notes, original.notes)


class TestBuiltinPresetsAndRegistry(unittest.TestCase):
    """Tests for BUILTIN_PRESETS list and PRESET_REGISTRY dict."""

    def test_builtin_presets_count(self):
        self.assertEqual(len(BUILTIN_PRESETS), 10)

    def test_preset_registry_length_matches_builtin(self):
        self.assertEqual(len(PRESET_REGISTRY), len(BUILTIN_PRESETS))

    def test_preset_registry_keys_are_preset_ids(self):
        for preset in BUILTIN_PRESETS:
            self.assertIn(preset.id, PRESET_REGISTRY)

    def test_preset_registry_values_are_motion_preset_instances(self):
        for key, value in PRESET_REGISTRY.items():
            self.assertIsInstance(value, MotionPreset)

    def test_known_preset_ids_present(self):
        expected_ids = {
            "pulse", "glow", "wobble", "bounce", "orbit",
            "glitch", "sparkle", "particle_burst", "laser_sweep", "signal_flash",
        }
        self.assertEqual(set(PRESET_REGISTRY.keys()), expected_ids)

    def test_orbit_not_sticker_safe(self):
        """orbit requires extra canvas — explicitly marked sticker_safe=False."""
        orbit = PRESET_REGISTRY["orbit"]
        self.assertFalse(orbit.sticker_safe)

    def test_particle_burst_not_sticker_safe_and_not_loopable(self):
        """Telegram animated stickers must loop; particle_burst is non-looping."""
        pb = PRESET_REGISTRY["particle_burst"]
        self.assertFalse(pb.sticker_safe)
        self.assertFalse(pb.loopable)

    def test_glitch_not_alpha_safe(self):
        """RGB channel splitting can alter transparency."""
        glitch = PRESET_REGISTRY["glitch"]
        self.assertFalse(glitch.alpha_safe)

    def test_all_presets_have_non_empty_id_and_name(self):
        for preset in BUILTIN_PRESETS:
            self.assertTrue(preset.id, f"Empty id on preset: {preset!r}")
            self.assertTrue(preset.name, f"Empty name on preset: {preset!r}")

    def test_all_preset_durations_positive(self):
        for preset in BUILTIN_PRESETS:
            self.assertGreater(preset.duration, 0, f"Non-positive duration on {preset.id}")

    def test_no_duplicate_ids_in_builtin_presets(self):
        ids = [p.id for p in BUILTIN_PRESETS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_preset_registry_built_from_builtin_presets(self):
        """PRESET_REGISTRY must map each preset's id to the same object from BUILTIN_PRESETS."""
        for preset in BUILTIN_PRESETS:
            self.assertIs(PRESET_REGISTRY[preset.id], preset)

    def test_builtin_presets_all_use_duration_field(self):
        """Regression: the new dataclass uses `duration`, not `duration_ms`."""
        for preset in BUILTIN_PRESETS:
            self.assertTrue(
                hasattr(preset, "duration"),
                f"Preset {preset.id} missing `duration` attribute",
            )
            self.assertFalse(
                hasattr(preset, "duration_ms"),
                f"Preset {preset.id} should not have `duration_ms` attribute",
            )

    def test_builtin_presets_all_use_notes_field(self):
        """Regression: the new dataclass uses `notes`, not `description`."""
        for preset in BUILTIN_PRESETS:
            self.assertTrue(
                hasattr(preset, "notes"),
                f"Preset {preset.id} missing `notes` attribute",
            )


class TestGetPreset(unittest.TestCase):
    """Tests for get_preset()."""

    def test_get_existing_preset_pulse(self):
        preset = get_preset("pulse")
        self.assertIsNotNone(preset)
        self.assertEqual(preset.id, "pulse")
        self.assertEqual(preset.name, "Pulse")

    def test_get_existing_preset_glitch(self):
        preset = get_preset("glitch")
        self.assertIsNotNone(preset)
        self.assertEqual(preset.id, "glitch")

    def test_get_non_existing_returns_none(self):
        result = get_preset("does_not_exist")
        self.assertIsNone(result)

    def test_get_empty_string_returns_none(self):
        result = get_preset("")
        self.assertIsNone(result)

    def test_get_case_sensitive(self):
        """IDs are lowercase slugs; uppercase should not match."""
        result = get_preset("Pulse")
        self.assertIsNone(result)

    def test_get_each_builtin_preset(self):
        for preset in BUILTIN_PRESETS:
            found = get_preset(preset.id)
            self.assertIsNotNone(found, f"get_preset('{preset.id}') returned None")
            self.assertIs(found, preset)

    def test_get_preset_returns_same_object_as_registry(self):
        result = get_preset("bounce")
        self.assertIs(result, PRESET_REGISTRY["bounce"])

    def test_get_particle_burst(self):
        preset = get_preset("particle_burst")
        self.assertIsNotNone(preset)
        self.assertFalse(preset.loopable)
        self.assertFalse(preset.sticker_safe)


class TestListPresets(unittest.TestCase):
    """Tests for list_presets() — the filter-capable version added in this PR.

    The catalog import is blocked at module load time (see top of file) so these
    tests exercise the __init__.py implementation, not catalog.py's simpler one.
    """

    def test_no_filters_returns_all_builtin_presets(self):
        result = list_presets()
        self.assertEqual(len(result), len(BUILTIN_PRESETS))

    def test_no_filters_returns_list_of_motion_presets(self):
        result = list_presets()
        for item in result:
            self.assertIsInstance(item, MotionPreset)

    def test_no_filters_order_preserved(self):
        """list_presets() with no args must preserve BUILTIN_PRESETS order."""
        result = list_presets()
        self.assertListEqual(result, BUILTIN_PRESETS)

    def test_filter_category_letter(self):
        result = list_presets(category="letter")
        for preset in result:
            self.assertTrue(
                not preset.recommended_categories or "letter" in preset.recommended_categories,
                f"Preset {preset.id} should not be returned for category='letter'",
            )

    def test_filter_category_includes_universal_presets(self):
        """Presets with empty recommended_categories match any category."""
        result = list_presets(category="letter")
        universal = [p for p in BUILTIN_PRESETS if not p.recommended_categories]
        for u in universal:
            self.assertIn(u, result)

    def test_filter_sticker_safe_true(self):
        result = list_presets(sticker_safe=True)
        for preset in result:
            self.assertTrue(preset.sticker_safe)
        ids = [p.id for p in result]
        self.assertNotIn("orbit", ids)
        self.assertNotIn("particle_burst", ids)

    def test_filter_sticker_safe_false(self):
        result = list_presets(sticker_safe=False)
        for preset in result:
            self.assertFalse(preset.sticker_safe)
        ids = [p.id for p in result]
        self.assertIn("orbit", ids)
        self.assertIn("particle_burst", ids)

    def test_filter_overlay_safe_true(self):
        result = list_presets(overlay_safe=True)
        for preset in result:
            self.assertTrue(preset.overlay_safe)

    def test_filter_overlay_safe_false(self):
        """Currently all built-ins are overlay_safe; result should be empty."""
        result = list_presets(overlay_safe=False)
        for preset in result:
            self.assertFalse(preset.overlay_safe)

    def test_filter_category_and_sticker_safe_combined(self):
        result = list_presets(category="particle", sticker_safe=False)
        for preset in result:
            self.assertFalse(preset.sticker_safe)
            self.assertTrue(
                not preset.recommended_categories or "particle" in preset.recommended_categories
            )

    def test_filter_category_no_match_returns_only_universal(self):
        """Unknown category returns only presets with empty recommended_categories."""
        result = list_presets(category="nonexistent_category_xyz")
        for preset in result:
            self.assertEqual(
                preset.recommended_categories, [],
                f"Preset {preset.id} has categories {preset.recommended_categories} "
                "but 'nonexistent_category_xyz' is not among them",
            )

    def test_filter_results_are_subset_of_builtin_presets(self):
        result = list_presets(sticker_safe=True)
        for item in result:
            self.assertIn(item, BUILTIN_PRESETS)

    def test_filter_category_signal(self):
        result = list_presets(category="signal")
        ids = [p.id for p in result]
        self.assertIn("glow", ids)
        self.assertIn("glitch", ids)
        self.assertIn("laser_sweep", ids)
        self.assertIn("signal_flash", ids)

    def test_filter_sticker_safe_none_returns_all(self):
        """sticker_safe=None (the default) must not filter by that flag."""
        result_none = list_presets(sticker_safe=None)
        result_all = list_presets()
        self.assertListEqual(result_none, result_all)

    def test_filter_overlay_safe_none_returns_all(self):
        result_none = list_presets(overlay_safe=None)
        result_all = list_presets()
        self.assertListEqual(result_none, result_all)

    def test_filter_category_none_returns_all(self):
        result_none = list_presets(category=None)
        result_all = list_presets()
        self.assertListEqual(result_none, result_all)

    def test_sticker_safe_false_filter_is_strict(self):
        """sticker_safe=False should NOT return presets where sticker_safe is True."""
        result = list_presets(sticker_safe=False)
        for preset in result:
            self.assertFalse(preset.sticker_safe)
            self.assertIsNot(preset.sticker_safe, True)


if __name__ == "__main__":
    unittest.main()
