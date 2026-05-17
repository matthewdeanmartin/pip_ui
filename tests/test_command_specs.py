"""Tests for command_specs module."""

from pip_ui.command_specs import COMMAND_GROUPS, COMMAND_SPECS
from pip_ui.models import SafetyLevel


def test_all_mvp_commands_present():
    required = {"install", "uninstall", "list", "show", "freeze", "check"}
    assert required.issubset(COMMAND_SPECS.keys())


def test_install_has_packages_field():
    spec = COMMAND_SPECS["install"]
    field_names = [a.name for a in spec.args]
    assert "packages" in field_names


def test_safety_levels_defined():
    for spec in COMMAND_SPECS.values():
        assert isinstance(spec.safety_level, SafetyLevel)


def test_command_groups_nonempty():
    assert len(COMMAND_GROUPS) > 0


def test_install_spec_fields():
    spec = COMMAND_SPECS["install"]
    field_names = [a.name for a in spec.args]
    assert "upgrade" in field_names
    assert "requirements_file" in field_names
    assert "no_cache_dir" in field_names


def test_list_has_format_dropdown():
    spec = COMMAND_SPECS["list"]
    format_arg = next((a for a in spec.args if a.name == "format"), None)
    assert format_arg is not None
    assert format_arg.field_type == "dropdown"
    assert "json" in format_arg.choices


def test_uninstall_safety_is_destructive():
    assert COMMAND_SPECS["uninstall"].safety_level == SafetyLevel.DESTRUCTIVE


def test_all_commands_have_labels():
    for name, spec in COMMAND_SPECS.items():
        assert spec.label, f"{name} has no label"
        assert spec.description, f"{name} has no description"
        assert spec.group, f"{name} has no group"
