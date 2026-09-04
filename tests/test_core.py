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


def test_parse_releases_from_github_payload():
    payload = [
        {
            "tag_name": "v0.7.0",
            "name": "Novo Início",
            "body": "## What's Changed\n* Dashboard by @user in http://x/pull/1\n\n**Full Changelog**: http://x",
            "html_url": "http://x/releases/v0.7.0",
            "published_at": "2026-09-01T10:00:00Z",
        },
        {"tag_name": "v0.6.1", "name": "", "draft": True},  # draft é ignorado
        {"tag_name": "0.6.0", "name": "Platinas", "body": "", "published_at": "2026-08-28T00:00:00Z"},
    ]
    notes = app_update.parse_releases(payload, limit=5)
    assert [n.version for n in notes] == ["0.7.0", "0.6.0"]  # tira o 'v' e pula draft
    assert notes[0].title == "Novo Início"
    assert notes[0].date == "2026-09-01"
    assert notes[1].version == "0.6.0"  # tag sem 'v' também funciona
    assert app_update.parse_releases({"nao": "lista"}) == []


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


def test_updater_script_renames_portable_folder():
    script = app_update.build_updater_script(
        Path("C:/base/StreamerSidekick-0.4.2-portable"),  # new_root (irrelevante aqui)
        Path("C:/base/StreamerSidekick-0.4.2-portable"),  # target: nome padrão
        Path("C:/staging"), 1, new_version="0.5.0",
    )
    assert "Rename-Item" in script
    assert "StreamerSidekick-0.5.0-portable" in script
    # sem new_version -> não renomeia
    plain = app_update.build_updater_script(Path("C:/new"), Path("C:/app"), Path("C:/s"), 1)
    assert "Rename-Item" not in plain


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


def test_fetch_catalog_forces_category(monkeypatch):
    from streamer_sidekick.core.plugins import CATEGORY_PLATINA, PluginManager
    mgr = PluginManager()
    # sem rede; entrada marcada como "tool" na fonte deve virar "platina"
    monkeypatch.setattr(mgr, "_fetch_remote_json", lambda url: None)
    monkeypatch.setattr(
        mgr, "_read_bundled_json",
        lambda path: {"plugins": [
            {"id": "g", "name": "G", "repo": "o/r", "module": "m", "category": "tool"}]},
    )
    plat = mgr.fetch_catalog(CATEGORY_PLATINA)
    assert plat and all(e.category == CATEGORY_PLATINA for e in plat)


def test_installed_filter_by_category(tmp_path, monkeypatch):
    import streamer_sidekick.core.plugins as plugins_mod
    from streamer_sidekick.core.plugins import CATEGORY_PLATINA, CATEGORY_TOOL
    monkeypatch.setattr(plugins_mod, "plugins_dir", lambda: tmp_path)

    for pid, cat in [("toolx", CATEGORY_TOOL), ("platx", CATEGORY_PLATINA)]:
        pkg = f"{pid}pkg"
        src = tmp_path / pid / "src" / pkg
        src.mkdir(parents=True)
        (src / "__init__.py").write_text("", encoding="utf-8")
        (src / "module.py").write_text(
            "def module_info():\n    return None\n"
            "def build_page(config=None):\n    return 'W'\n",
            encoding="utf-8",
        )
        (tmp_path / pid / "plugin.json").write_text(
            json.dumps({"id": pid, "name": pid, "version": "1.0.0",
                        "src_subdir": "src", "module": f"{pkg}.module", "category": cat}),
            encoding="utf-8",
        )

    mgr = plugins_mod.PluginManager()
    mgr.load()
    assert {p.id for p in mgr.installed(CATEGORY_TOOL)} == {"toolx"}
    assert {p.id for p in mgr.installed(CATEGORY_PLATINA)} == {"platx"}
    assert len(mgr.installed()) == 2


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


def test_hotkey_backend_uses_one_listener(monkeypatch):
    """Fora do Windows, TODOS os atalhos precisam caber num listener so.

    O pynput traduz teclas via Carbon, que nao aguenta chamadas concorrentes:
    tres listeners vivos ao mesmo tempo abortam o processo no macOS (SIGABRT,
    sem excecao). O app registra cinco atalhos no hub mais um por overlay de
    contador, entao este teste trava o invariante.
    """
    if hotkey_backend._ON_WINDOWS:  # no Windows cada atalho e um hook, sem listener
        return

    started: list[dict] = []

    class FakeListener:
        def __init__(self, mapping):
            self.mapping = mapping
            self.alive = False

        def start(self):
            self.alive = True
            started.append(self.mapping)

        def stop(self):
            self.alive = False

        def join(self, timeout=None):
            pass

    class FakeKeyboard:
        GlobalHotKeys = FakeListener

    monkeypatch.setattr(hotkey_backend, "_pynput_keyboard", FakeKeyboard)
    monkeypatch.setattr(hotkey_backend, "_entries", {})
    monkeypatch.setattr(hotkey_backend, "_listener", None)

    hub = hotkey_backend.register_batch({
        "Ctrl+Alt+H": lambda: None,
        "Ctrl+Alt+M": lambda: None,
    })
    overlay_a = hotkey_backend.register("Ctrl+Alt+1", lambda: None)
    overlay_b = hotkey_backend.register("Ctrl+Alt+2", lambda: None)

    # Um unico listener vivo, com todos os combos.
    assert hotkey_backend._listener is not None
    assert hotkey_backend._listener.alive
    assert set(started[-1]) == {"<ctrl>+<alt>+h", "<ctrl>+<alt>+m", "<ctrl>+<alt>+1", "<ctrl>+<alt>+2"}

    hotkey_backend.unregister(overlay_a)
    assert set(started[-1]) == {"<ctrl>+<alt>+h", "<ctrl>+<alt>+m", "<ctrl>+<alt>+2"}

    hotkey_backend.unregister(overlay_b)
    hotkey_backend.unregister(hub)
    assert hotkey_backend._listener is None


def test_hotkey_same_combo_fires_every_callback(monkeypatch):
    """Dois contadores no mesmo atalho: os dois devem contar.

    Como o mapa do pynput e um dicionario, sem agrupar os callbacks o segundo
    registro sobrescreveria o primeiro em silencio.
    """
    if hotkey_backend._ON_WINDOWS:
        return

    mappings: list[dict] = []

    class FakeListener:
        def __init__(self, mapping):
            mappings.append(mapping)

        def start(self):
            pass

        def stop(self):
            pass

        def join(self, timeout=None):
            pass

    class FakeKeyboard:
        GlobalHotKeys = FakeListener

    monkeypatch.setattr(hotkey_backend, "_pynput_keyboard", FakeKeyboard)
    monkeypatch.setattr(hotkey_backend, "_entries", {})
    monkeypatch.setattr(hotkey_backend, "_listener", None)

    fired: list[str] = []
    hotkey_backend.register("Ctrl+Alt+1", lambda: fired.append("a"))
    hotkey_backend.register("Ctrl+Alt+1", lambda: fired.append("b"))

    mappings[-1]["<ctrl>+<alt>+1"]()
    assert fired == ["a", "b"]


def test_net_uses_certifi_when_present():
    """O contexto TLS do app nao pode depender do cert store da maquina.

    No macOS o Python do python.org nao usa o Keychain: sem isto, catalogo de
    plugins, feed de novidades e instalacao morrem com CERTIFICATE_VERIFY_FAILED.
    """
    from streamer_sidekick.core import net

    net.ssl_context.cache_clear()
    context = net.ssl_context()
    try:
        import certifi
    except ImportError:
        assert context is None  # sem certifi caimos no padrao do sistema
        return
    assert context is not None
    assert context.verify_mode.name == "CERT_REQUIRED"
    assert context.cert_store_stats()["x509_ca"] > 0
