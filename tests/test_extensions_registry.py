"""Tests for the extension hook registry system."""

from plmux.extensions.registry import (
    ExtensionContext,
    _PLUGIN_OWNERS,
    _REGISTRY,
    _PLUGIN_COMMANDS,
    _CONFIG_HOOKS,
    _last_emit,
    get_plugin_commands,
    load_config_hooks,
    register_command,
    register_hook,
    emit_hook,
)


class TestRegisterHook:
    def setup_method(self):
        _REGISTRY.clear()
        _PLUGIN_OWNERS.clear()
        _last_emit.clear()
        _CONFIG_HOOKS.clear()

    def test_register_and_emit_hook(self):
        received = []

        def my_hook(ctx):
            received.append(ctx.hook_name)

        register_hook("app_started", my_hook)
        emit_hook("app_started", ExtensionContext(hook_name="app_started"))
        assert received == ["app_started"]

    def test_multiple_hooks_on_same_event(self):
        received = []

        def h1(ctx):
            received.append("h1")

        def h2(ctx):
            received.append("h2")

        register_hook("app_started", h1)
        register_hook("app_started", h2)
        emit_hook("app_started", ExtensionContext())
        assert received == ["h1", "h2"]

    def test_no_hook_registered_does_not_raise(self):
        emit_hook("app_started", ExtensionContext())

    def test_hook_exception_does_not_crash(self):
        received = []

        def bad_hook(ctx):
            raise RuntimeError("hook failed")

        def good_hook(ctx):
            received.append("ok")

        register_hook("app_started", bad_hook)
        register_hook("app_started", good_hook)
        emit_hook("app_started", ExtensionContext())
        assert received == ["ok"]

    def test_config_hook_executes(self):
        _CONFIG_HOOKS["app_started"] = ["echo hello"]
        emit_hook("app_started", ExtensionContext())

    def test_throttle_skips_fast_emits(self):
        first = []

        def h(ctx):
            first.append(1)

        register_hook("status_refresh", h)
        emit_hook("status_refresh", ExtensionContext())
        assert len(first) == 1
        emit_hook("status_refresh", ExtensionContext())
        assert len(first) == 1

    def test_throttle_allows_after_time(self):
        received = []
        import time

        def h(ctx):
            received.append(1)

        _last_emit["status_refresh"] = time.monotonic() - 10
        register_hook("status_refresh", h)
        emit_hook("status_refresh", ExtensionContext())
        assert len(received) == 1


class TestRegisterCommand:
    def setup_method(self):
        _PLUGIN_COMMANDS.clear()
        _PLUGIN_OWNERS.clear()

    def test_register_and_get_commands(self):
        def my_cmd(ctx):
            pass

        register_command("my-command", my_cmd)
        cmds = get_plugin_commands()
        assert "my-command" in cmds
        assert cmds["my-command"] is my_cmd

    def test_empty_command_list(self):
        assert get_plugin_commands() == {}


class TestLoadConfigHooks:
    def setup_method(self):
        _CONFIG_HOOKS.clear()

    def test_load_config_hooks(self):
        hooks = {
            "app_started": ["echo start"],
            "app_stopping": ["echo stop"],
        }
        load_config_hooks(hooks)
        assert _CONFIG_HOOKS["app_started"] == ["echo start"]
        assert _CONFIG_HOOKS["app_stopping"] == ["echo stop"]

    def test_load_config_hooks_clears_previous(self):
        _CONFIG_HOOKS["app_started"] = ["old"]
        load_config_hooks({"app_started": ["new"]})
        assert _CONFIG_HOOKS["app_started"] == ["new"]
