"""Testes de unidade da lógica pura (rodam sem display, rápidos no CI)."""
import json
from pathlib import Path

from streamer_sidekick.core import app_update, hotkey_backend
from streamer_sidekick.core.plugins import CatalogEntry, PluginManager, version_tuple


def test_version_tuple_compare():
    assert version_tuple("1.2.0") > version_tuple("1.1.9")
    assert version_tuple("2.0.0") > version_tuple("1.9.9")
    assert version_tuple("0.4.10") > version_tuple("0.4.9")  # numérico, não string
    assert not (version_tuple("1.0.0") > version_tuple("1.0.0"))


def test_hotkey_to_pynput():
    assert hotkey_backend._to_pynput("Ctrl+Alt+H") == "<ctrl>+<alt>+h"
    assert hotkey_backend._to_pynput("Ctrl+Alt+Shift+C") == "<ctrl>+<alt>+<shift>+c"
    assert hotkey_backend._to_pynput("Ctrl+Alt+F5") == "<ctrl>+<alt>+<f5>"
    assert hotkey_backend._to_pynput("Cmd+Space") == "<cmd>+<space>"


def test_catalog_entry_from_dict():
    entry = CatalogEntry.from_dict({
        "id": "launcher", "name": "StreamOn", "repo": "o/r",
        "version": "1.0.1", "module": "m", "icon": "i.png",
        "changelog": "novidades", "min_sidekick_version": "0.4.0",
    })
    assert entry is not None
    assert entry.id == "launcher" and entry.version == "1.0.1"
    assert entry.icon == "i.png" and entry.min_sidekick_version == "0.4.0"
    # 'repo' obrigatório ausente -> None
    assert CatalogEntry.from_dict({"id": "x"}) is None


def test_catalog_zip_url():
    entry = CatalogEntry(id="x", name="X", description="", repo="dono/repo", ref="main")
    assert entry.zip_url() == "https://github.com/dono/repo/archive/refs/heads/main.zip"


def test_plugin_compatibility():
    mgr = PluginManager()
    ok = CatalogEntry(id="a", name="A", description="", repo="o/r", min_sidekick_version="0.0.1")
    bad = CatalogEntry(id="b", name="B", description="", repo="o/r", min_sidekick_version="99.0.0")
    assert mgr.is_compatible(ok)
    assert not mgr.is_compatible(bad)
    assert "99.0.0" in (mgr.incompatibility_reason(bad) or "")


def test_updater_script_is_powershell():
    script = app_update.build_updater_script(
        Path("C:/new"), Path("C:/app"), Path("C:/staging"), 4242,
    )
    assert "Wait-Process -Id 4242" in script
    assert "robocopy" in script
    assert "StreamerSidekick.exe" in script
    assert "Remove-Item -LiteralPath $PSCommandPath" in script
    # sem os construtos frágeis do .bat antigo que travavam sem console
    assert "tasklist" not in script
    assert "timeout /t" not in script


def test_plugin_discovery(tmp_path, monkeypatch):
    import streamer_sidekick.core.plugins as plugins_mod
    monkeypatch.setattr(plugins_mod, "plugins_dir", lambda: tmp_path)

    src = tmp_path / "demo" / "src" / "demopkg"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "module.py").write_text(
        "def module_info():\n    return None\n"
        "def build_page(config=None):\n    return 'W'\n",
        encoding="utf-8",
    )
    (tmp_path / "demo" / "plugin.json").write_text(
        json.dumps({
            "id": "demo", "name": "Demo", "version": "1.0.0",
            "src_subdir": "src", "module": "demopkg.module",
        }),
        encoding="utf-8",
    )

    mgr = PluginManager()
    mgr.load()
    plugin = mgr.get("demo")
    assert plugin is not None
    assert plugin.loaded and plugin.error is None
    assert callable(plugin.build_page)


def test_plugin_discovery_incompatible(tmp_path, monkeypatch):
    import streamer_sidekick.core.plugins as plugins_mod
    monkeypatch.setattr(plugins_mod, "plugins_dir", lambda: tmp_path)

    (tmp_path / "future").mkdir()
    (tmp_path / "future" / "plugin.json").write_text(
        json.dumps({
            "id": "future", "name": "Future", "version": "1.0.0",
            "module": "x.y", "min_sidekick_version": "99.0.0",
        }),
        encoding="utf-8",
    )
    mgr = PluginManager()
    mgr.load()
    plugin = mgr.get("future")
    assert plugin is not None
    assert not plugin.loaded
    assert "99.0.0" in (plugin.error or "")
