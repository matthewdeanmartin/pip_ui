"""Tests for forms.build_argv_for_spec and related argv generation."""

from __future__ import annotations

from pip_ui.command_specs import COMMAND_SPECS
from pip_ui.forms import (
    GLOBAL_OPTIONS,
    build_argv_for_spec,
    parse_raw_extra,
    render_global_args,
)


def get_defaults(name: str) -> dict[str, object]:
    """Return a dict of arg.name -> default value for the named command."""
    spec = COMMAND_SPECS[name]
    out: dict[str, object] = {}
    for arg in spec.args:
        if arg.field_type == "checkbox":
            out[arg.name] = bool(arg.default)
        else:
            out[arg.name] = arg.default
    return out


def test_install_basic_argv():
    values = get_defaults("install")
    values["packages"] = "requests"
    argv = build_argv_for_spec(COMMAND_SPECS["install"], values)
    assert argv[0] == "install"
    assert "requests" in argv


def test_install_upgrade_argv():
    values = get_defaults("install")
    values["packages"] = "requests"
    values["upgrade"] = True
    argv = build_argv_for_spec(COMMAND_SPECS["install"], values)
    assert "-U" in argv
    assert "requests" in argv


def test_install_extra_index_emits_flag_per_token():
    values = get_defaults("install")
    values["packages"] = "requests"
    values["extra_index_url"] = "https://a/simple https://b/simple"
    argv = build_argv_for_spec(COMMAND_SPECS["install"], values)
    assert argv.count("--extra-index-url") == 2
    assert "https://a/simple" in argv
    assert "https://b/simple" in argv


def test_install_dropdown_only_emits_when_non_default():
    values = get_defaults("install")
    values["packages"] = "requests"
    # upgrade_strategy default is "only-if-needed" — should NOT be emitted
    argv = build_argv_for_spec(COMMAND_SPECS["install"], values)
    assert "--upgrade-strategy" not in argv

    values["upgrade_strategy"] = "eager"
    argv = build_argv_for_spec(COMMAND_SPECS["install"], values)
    assert "--upgrade-strategy" in argv
    assert "eager" in argv


def test_install_empty_editable_skipped():
    """Empty editable string must NOT inject a stray empty argv entry."""
    values = get_defaults("install")
    values["packages"] = "requests"
    values["editable"] = ""
    argv = build_argv_for_spec(COMMAND_SPECS["install"], values)
    assert "" not in argv
    assert "-e" not in argv


def test_uninstall_argv():
    values = get_defaults("uninstall")
    values["packages"] = "requests flask"
    values["yes"] = True
    argv = build_argv_for_spec(COMMAND_SPECS["uninstall"], values)
    assert argv[0] == "uninstall"
    assert "-y" in argv
    assert "requests" in argv
    assert "flask" in argv


def test_list_argv_json_format():
    values = get_defaults("list")
    values["format"] = "json"
    argv = build_argv_for_spec(COMMAND_SPECS["list"], values)
    assert "list" in argv
    assert "--format" in argv
    assert "json" in argv


def test_list_argv_default_format_omitted():
    values = get_defaults("list")
    argv = build_argv_for_spec(COMMAND_SPECS["list"], values)
    assert "--format" not in argv


def test_show_with_packages():
    values = get_defaults("show")
    values["packages"] = "requests"
    values["files"] = True
    argv = build_argv_for_spec(COMMAND_SPECS["show"], values)
    assert argv[0] == "show"
    assert "requests" in argv
    assert "-f" in argv


def test_freeze_argv():
    values = get_defaults("freeze")
    values["exclude_editable"] = True
    argv = build_argv_for_spec(COMMAND_SPECS["freeze"], values)
    assert argv[0] == "freeze"
    assert "--exclude-editable" in argv


def test_check_argv():
    argv = build_argv_for_spec(COMMAND_SPECS["check"], {})
    assert argv == ["check"]


def test_inspect_argv():
    values = get_defaults("inspect")
    values["local"] = True
    argv = build_argv_for_spec(COMMAND_SPECS["inspect"], values)
    assert argv[0] == "inspect"
    assert "--local" in argv


def test_index_versions_argv():
    values = get_defaults("index_versions")
    values["package"] = "requests"
    values["pre"] = True
    argv = build_argv_for_spec(COMMAND_SPECS["index_versions"], values)
    assert argv[:2] == ["index", "versions"]
    assert "requests" in argv
    assert "--pre" in argv


def test_download_argv_with_dest():
    values = get_defaults("download")
    values["packages"] = "requests"
    values["dest"] = "./wheelhouse"
    argv = build_argv_for_spec(COMMAND_SPECS["download"], values)
    assert argv[0] == "download"
    assert "-d" in argv
    assert "./wheelhouse" in argv


def test_wheel_argv():
    values = get_defaults("wheel")
    values["packages"] = "requests"
    values["wheel_dir"] = "./wheels"
    argv = build_argv_for_spec(COMMAND_SPECS["wheel"], values)
    assert argv[0] == "wheel"
    assert "-w" in argv
    assert "./wheels" in argv


def test_config_list_special():
    argv = build_argv_for_spec(COMMAND_SPECS["config_list"], {})
    assert argv == ["config", "list"]


def test_config_debug_special():
    argv = build_argv_for_spec(COMMAND_SPECS["config_debug"], {})
    assert argv == ["config", "debug"]


def test_config_get_argv():
    argv = build_argv_for_spec(COMMAND_SPECS["config_get"], {"key": "global.index-url"})
    assert argv == ["config", "get", "global.index-url"]


def test_config_set_argv_scope_user():
    values = {"scope": "user", "key": "global.index-url", "value": "https://example.com/simple/"}
    argv = build_argv_for_spec(COMMAND_SPECS["config_set"], values)
    assert argv == ["config", "--user", "set", "global.index-url", "https://example.com/simple/"]


def test_config_set_argv_scope_global():
    values = {"scope": "global", "key": "foo", "value": "bar"}
    argv = build_argv_for_spec(COMMAND_SPECS["config_set"], values)
    assert argv == ["config", "--global", "set", "foo", "bar"]


def test_config_unset_argv():
    argv = build_argv_for_spec(COMMAND_SPECS["config_unset"], {"scope": "user", "key": "global.index-url"})
    assert argv == ["config", "--user", "unset", "global.index-url"]


def test_config_edit_argv():
    argv = build_argv_for_spec(COMMAND_SPECS["config_edit"], {"scope": "user"})
    assert argv == ["config", "--user", "edit"]


def test_cache_dir_special():
    assert build_argv_for_spec(COMMAND_SPECS["cache_dir"], {}) == ["cache", "dir"]


def test_cache_info_special():
    assert build_argv_for_spec(COMMAND_SPECS["cache_info"], {}) == ["cache", "info"]


def test_cache_purge_special():
    assert build_argv_for_spec(COMMAND_SPECS["cache_purge"], {}) == ["cache", "purge"]


def test_cache_list_argv():
    argv = build_argv_for_spec(COMMAND_SPECS["cache_list"], {"pattern": "requests*", "format": "abspath"})
    assert argv[:2] == ["cache", "list"]
    assert "requests*" in argv
    assert "--format" in argv
    assert "abspath" in argv


def test_cache_list_format_default_omitted():
    argv = build_argv_for_spec(COMMAND_SPECS["cache_list"], {"pattern": "requests*", "format": "human"})
    assert "--format" not in argv


def test_cache_remove_argv():
    argv = build_argv_for_spec(COMMAND_SPECS["cache_remove"], {"pattern": "requests*"})
    assert argv == ["cache", "remove", "requests*"]


def test_version_special():
    assert build_argv_for_spec(COMMAND_SPECS["version"], {}) == ["--version"]


def test_help_special():
    assert build_argv_for_spec(COMMAND_SPECS["help"], {}) == ["help"]


def test_render_global_args_verbose():
    values = {"g_verbose": True}
    out = render_global_args(values)
    assert "-v" in out


def test_render_global_args_proxy():
    values = {"g_proxy": "http://proxy.example.com:8080"}
    out = render_global_args(values)
    assert "--proxy" in out
    assert "http://proxy.example.com:8080" in out


def test_render_global_args_empty():
    assert not render_global_args({})


def test_global_options_listing_is_non_empty():
    assert len(GLOBAL_OPTIONS) > 5


def test_parse_raw_extra_simple():
    assert parse_raw_extra("--foo bar baz") == ["--foo", "bar", "baz"]


def test_parse_raw_extra_quoted():
    assert parse_raw_extra('--name "hello world" x') == ["--name", "hello world", "x"]


def test_parse_raw_extra_empty():
    assert parse_raw_extra("") == []
