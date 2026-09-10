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
    if hotkey_backend._ON_WINDOWS or hotkey_backend._ON_MACOS:
        return  # so o caminho do pynput (Linux) tem listener

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

    hub_h = hotkey_backend.register("Ctrl+Alt+H", lambda: None)
    hub_m = hotkey_backend.register("Ctrl+Alt+M", lambda: None)
    overlay_a = hotkey_backend.register("Ctrl+Alt+1", lambda: None)
    overlay_b = hotkey_backend.register("Ctrl+Alt+2", lambda: None)

    # Um unico listener vivo, com todos os combos.
    assert hotkey_backend._listener is not None
    assert hotkey_backend._listener.alive
    assert set(started[-1]) == {"<ctrl>+<alt>+h", "<ctrl>+<alt>+m", "<ctrl>+<alt>+1", "<ctrl>+<alt>+2"}

    hotkey_backend.unregister(overlay_a)
    assert set(started[-1]) == {"<ctrl>+<alt>+h", "<ctrl>+<alt>+m", "<ctrl>+<alt>+2"}

    hotkey_backend.unregister(overlay_b)
    hotkey_backend.unregister(hub_h)
    hotkey_backend.unregister(hub_m)
    assert hotkey_backend._listener is None


def test_hotkey_same_combo_fires_every_callback(monkeypatch):
    """Dois contadores no mesmo atalho: os dois devem contar.

    Como o mapa do pynput e um dicionario, sem agrupar os callbacks o segundo
    registro sobrescreveria o primeiro em silencio.
    """
    if hotkey_backend._ON_WINDOWS or hotkey_backend._ON_MACOS:
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


def test_net_context_always_has_roots():
    """O contexto TLS do app precisa ter raizes em qualquer plataforma.

    No macOS o Python do python.org nao usa o Keychain, entao o padrao vem vazio
    e catalogo, feed de novidades e instalacao morrem com
    CERTIFICATE_VERIFY_FAILED. O certifi cobre esse buraco.
    """
    from streamer_sidekick.core import net

    net.ssl_context.cache_clear()
    context = net.ssl_context()
    assert context.verify_mode.name == "CERT_REQUIRED"
    assert context.cert_store_stats()["x509_ca"] > 0


def test_net_keeps_system_store_when_it_works():
    """Onde a loja do sistema funciona (Windows), nao a substituimos.

    Trocar a loja do Windows pelo certifi quebraria quem esta atras de um proxy
    corporativo com raiz propria -- o certifi so entra quando o padrao vem vazio.
    """
    import ssl

    from streamer_sidekick.core import net

    net.ssl_context.cache_clear()
    system = ssl.create_default_context()
    context = net.ssl_context()

    if net._has_roots(system):
        assert context.cert_store_stats() == system.cert_store_stats()
    else:
        assert context.cert_store_stats()["x509_ca"] > 0


# ---- auto-update multiplataforma ------------------------------------------

_MANIFEST = {
    "version": "9.9.9",
    "zip_url": "https://exemplo/win.zip",
    "notes": "novidades",
    "platforms": {
        "windows": {"zip_url": "https://exemplo/win.zip"},
        "macos": {"zip_url": "https://exemplo/mac.zip"},
    },
}


def test_manifest_picks_the_right_platform():
    win = app_update.release_from_manifest(_MANIFEST, "windows")
    mac = app_update.release_from_manifest(_MANIFEST, "macos")
    assert win is not None and win.zip_url == "https://exemplo/win.zip"
    assert mac is not None and mac.zip_url == "https://exemplo/mac.zip"
    # version e notes caem para a raiz quando a secao nao repete
    assert mac.version == "9.9.9" and mac.notes == "novidades"


def test_manifest_sem_secao_de_plataforma_ainda_serve_o_windows():
    """Clientes ja instalados leem so os campos soltos da raiz.

    Se a raiz deixasse de ser o manifesto do Windows, todo mundo que ja tem o
    app instalado ficaria sem update para sempre -- eles nao conhecem
    "platforms".
    """
    legado = {"version": "9.9.9", "zip_url": "https://exemplo/win.zip"}
    assert app_update.release_from_manifest(legado, "windows") is not None
    # Mas nao inventamos um download para um sistema que a Release nao anuncia.
    assert app_update.release_from_manifest(legado, "macos") is None


def test_manifest_incompleto_nao_vira_release():
    assert app_update.release_from_manifest({"version": "9.9.9"}, "windows") is None
    assert app_update.release_from_manifest({"zip_url": "x"}, "windows") is None
    assert app_update.release_from_manifest(None, "windows") is None


def test_updater_macos_troca_o_bundle_com_seguranca():
    """O script so pode apagar o app antigo DEPOIS de copiar o novo.

    Se a ordem inverter, uma falha no meio do caminho deixa o usuario sem app
    nenhum -- e sem app nao ha como tentar de novo.
    """
    script = app_update.build_updater_sh(
        Path("/tmp/stg/Streamer Sidekick.app"),
        Path("/Applications/Streamer Sidekick.app"),
        Path("/tmp/stg"),
        4321,
    )
    assert script.startswith("#!/bin/sh")
    assert "PID=4321" in script
    # ditto, nao cp -R: o bundle e cheio de symlinks.
    assert "ditto" in script
    copia = script.index('ditto "$NEW" "$NEXT"')
    remocao = script.index('rm -rf "$TARGET"')
    assert copia < remocao
    # e o app volta a abrir sozinho
    assert 'open "$TARGET"' in script


def test_updater_macos_lida_com_espaco_e_apostrofo_no_caminho():
    """'Streamer Sidekick.app' tem espaco; a home do usuario pode ter apostrofo.

    Usa PurePosixPath porque este teste tambem roda no Windows, onde um
    ``Path("/Users/...")`` viraria ``\\Users\\...`` e mediria a conversao de
    separador em vez do que interessa, que e o aspeamento.
    """
    import shlex
    from pathlib import PurePosixPath

    destino = "/Users/ric's mac/Streamer Sidekick.app"
    script = app_update.build_updater_sh(
        PurePosixPath("/tmp/stg/Streamer Sidekick.app"),
        PurePosixPath(destino),
        PurePosixPath("/tmp/stg"),
        1,
    )
    linha = [l for l in script.splitlines() if l.startswith("TARGET=")][0]
    # shlex.quote devolve algo que o shell le como UM argumento so
    assert shlex.split(linha[len("TARGET="):]) == [destino]


def test_can_self_update_por_plataforma(monkeypatch):
    monkeypatch.setattr(app_update, "is_frozen", lambda: True)
    for plataforma, esperado in (("win32", True), ("darwin", True), ("linux", False)):
        monkeypatch.setattr(app_update.sys, "platform", plataforma)
        assert app_update.can_self_update() is esperado
    # rodando do codigo-fonte, nunca
    monkeypatch.setattr(app_update, "is_frozen", lambda: False)
    monkeypatch.setattr(app_update.sys, "platform", "darwin")
    assert app_update.can_self_update() is False


def test_install_dir_no_macos_e_o_bundle_inteiro(monkeypatch):
    """No macOS o updater apaga o que install_dir() devolver.

    Se devolvesse a pasta do executável (Contents/MacOS), o update destruiria as
    tripas do bundle e deixaria um .app quebrado. Tem que ser o .app inteiro.
    """
    monkeypatch.setattr(app_update, "is_frozen", lambda: True)
    monkeypatch.setattr(app_update.sys, "platform", "darwin")
    exe = "/Applications/Streamer Sidekick.app/Contents/MacOS/StreamerSidekick"
    monkeypatch.setattr(app_update.sys, "executable", exe)

    resultado = app_update.install_dir()
    # Compara com a mesma resolucao que a funcao faz: no Windows (onde este teste
    # tambem roda) um caminho absoluto POSIX ganha a letra do drive.
    assert resultado == Path(exe).resolve().parents[2]
    assert resultado.name == "Streamer Sidekick.app"


def test_install_dir_no_windows_e_a_pasta_do_exe(monkeypatch):
    monkeypatch.setattr(app_update, "is_frozen", lambda: True)
    monkeypatch.setattr(app_update.sys, "platform", "win32")
    exe = "/portable/StreamerSidekick/StreamerSidekick.exe"
    monkeypatch.setattr(app_update.sys, "executable", exe)
    assert app_update.install_dir() == Path(exe).resolve().parent


# ---- permissões de macOS ---------------------------------------------------


def test_pynput_nunca_le_o_layout_na_thread_do_listener(monkeypatch):
    """O HIToolbox exige a thread principal; ler de outra mata o processo.

    O pynput lê o layout de dentro da thread do listener. Como não dá para
    mudar isso, trocamos o `keycode_context` dele por um que devolve um valor
    lido na thread principal. Este teste trava a troca: se um upgrade do pynput
    mudar o nome ou o local da função, ele quebra aqui — e não com um SIGTRAP
    na máquina do usuário.
    """
    if hotkey_backend._ON_WINDOWS or hotkey_backend._ON_MACOS:
        return  # o macOS usa a API nativa; nao passa pelo pynput

    monkeypatch.setattr(hotkey_backend, "_keycode_patch_failed", False)

    hotkey_backend._refresh_keycode_snapshot()

    from pynput._util import darwin as util_darwin
    from pynput.keyboard import _darwin as kb_darwin

    # os dois lugares precisam apontar para o nosso, porque o keyboard/_darwin
    # importa o nome direto
    assert util_darwin.keycode_context.__name__ == "_snapshot_context"
    assert kb_darwin.keycode_context.__name__ == "_snapshot_context"
    assert hotkey_backend.keycode_snapshot_ok()

    # e o valor entregue precisa ser utilizável (tipo de teclado + layout)
    with kb_darwin.keycode_context() as contexto:
        tipo, layout = contexto
    assert tipo is not None and layout


def test_snapshot_nao_le_fora_da_thread_principal():
    """Chamado de outra thread, o refresh não pode tocar no HIToolbox."""
    import threading

    if hotkey_backend._ON_WINDOWS or hotkey_backend._ON_MACOS:
        return

    chamou = []
    resultado = []

    def de_outra_thread():
        antes = hotkey_backend._keycode_snapshot
        hotkey_backend._refresh_keycode_snapshot()
        resultado.append(hotkey_backend._keycode_snapshot is antes)

    t = threading.Thread(target=de_outra_thread)
    t.start()
    t.join()
    assert resultado == [True], "o refresh mexeu no snapshot fora da thread principal"


# ---- atalhos nativos do macOS ---------------------------------------------


def test_carbon_traduz_a_notacao_para_teclas_fisicas():
    """"Ctrl" tem que virar a tecla Control, e "Cmd" a tecla Command.

    É onde o Qt confunde: para ele, no macOS, "Ctrl" significa Command. Se o
    backend herdasse essa troca, o atalho mostrado na tela dispararia com
    outra combinação — foi exatamente o que aconteceu na v0.7.3.
    """
    if not hotkey_backend._ON_MACOS:
        return
    from streamer_sidekick.core import hotkey_backend_carbon as carbon

    _, mods = carbon.parse("Ctrl+Alt+M")
    assert mods & 0x1000  # controlKey -> tecla Control física
    assert mods & 0x0800  # optionKey
    assert not mods & 0x0100  # e NÃO Command

    _, mods = carbon.parse("Cmd+Alt+M")
    assert mods & 0x0100 and not mods & 0x1000

    codigo_m, _ = carbon.parse("Ctrl+Alt+M")
    assert codigo_m == 46  # virtual keycode do M


def test_carbon_recusa_atalhos_impossiveis():
    if not hotkey_backend._ON_MACOS:
        return
    import pytest

    from streamer_sidekick.core import hotkey_backend_carbon as carbon

    with pytest.raises(ValueError):
        carbon.parse("M")  # sem modificador engoliria a tecla no sistema todo
    with pytest.raises(ValueError):
        carbon.parse("Ctrl+Alt+Ç")  # sem virtual keycode
    with pytest.raises(ValueError):
        carbon.parse("Ctrl+Alt")  # só modificadores


def test_macos_usa_a_api_nativa_e_nao_o_pynput():
    """É esta escolha que torna a permissão de Acessibilidade desnecessária.

    Se algum dia o macOS voltar ao pynput, a permissão volta a ser obrigatória
    e os atalhos param de disparar em silêncio — este teste é o alarme.
    """
    if hotkey_backend._ON_MACOS:
        assert hotkey_backend.backend_name() == "carbon"
        assert hotkey_backend._pynput_keyboard is None
    elif hotkey_backend._ON_WINDOWS:
        assert hotkey_backend.backend_name() == "keyboard"


# ---- conversão de atalho entre o Qt e a notação do app ---------------------


def _app_qt():
    """QApplication única para os testes que precisam do Qt."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_o_que_a_tela_mostra_e_o_que_dispara():
    """O símbolo exibido tem que ser a tecla que realmente aciona o atalho.

    No macOS o Qt renderiza `Ctrl+Alt+M` como ⌥⌘M (Option+Command), mas o
    atalho dispara com Control+Option. A tela mentia para o usuário.
    """
    _app_qt()
    from streamer_sidekick.core import hotkey_text

    exibido = hotkey_text.to_display("Ctrl+Alt+M")
    if hotkey_backend._ON_MACOS:
        assert exibido == "⌃⌥M"  # Control+Option, não ⌘
        assert "⌘" not in exibido

        from streamer_sidekick.core import hotkey_backend_carbon as carbon

        _, mods = carbon.parse("Ctrl+Alt+M")
        # o que a tela mostra bate com o que o sistema registra
        assert bool(mods & 0x1000) == ("⌃" in exibido)
        assert bool(mods & 0x0100) == ("⌘" in exibido)
    else:
        assert exibido == "Ctrl+Alt+M"


def test_gravar_atalho_nao_salva_simbolos():
    """Gravar tem que produzir notação, não a string de símbolos do Qt.

    Antes salvava `toString(NativeText)` — no macOS a string "⌥⌘M". Nenhum
    backend interpreta isso, então trocar um atalho no Mac o quebrava para
    sempre.
    """
    _app_qt()
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeySequence

    from streamer_sidekick.core import hotkey_text

    if hotkey_backend._ON_MACOS:
        # No Mac, o usuário apertando Control+Option+M chega no Qt como Meta+Alt
        pressionado = QKeySequence(
            Qt.KeyboardModifier.MetaModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.Key.Key_M
        )
    else:
        pressionado = QKeySequence(
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.AltModifier
            | Qt.Key.Key_M
        )

    gravado = hotkey_text.from_key_sequence(pressionado)
    assert gravado == "Ctrl+Alt+M"
    assert "⌘" not in gravado and "⌥" not in gravado
    # e o backend do sistema aceita o que foi gravado
    hotkey_backend.validate(gravado)


def test_ida_e_volta_do_atalho():
    """Notação -> campo da tela -> notação tem que fechar."""
    _app_qt()
    from streamer_sidekick.core import hotkey_text

    for texto in ("Ctrl+Alt+M", "Ctrl+Alt+Shift+C", "Ctrl+Alt+H"):
        volta = hotkey_text.from_key_sequence(hotkey_text.to_key_sequence(texto))
        assert volta == texto, f"{texto} virou {volta}"


def test_aceita_atalho_salvo_como_simbolo():
    """Presets antigos gravaram "⌃⌥2" em vez da notação — têm que continuar valendo.

    Era o que quebrava o contador: o preset guardava a string renderizada, o
    backend não conseguia interpretar, e o atalho nunca chegava a ser
    registrado. O contador simplesmente não subia, sem nenhum aviso.
    """
    # Fora do macOS não existe esse formato, e normalize() é identidade: o
    # Windows nunca gravou símbolos, então converter lá seria mexer à toa.
    if not hotkey_backend._ON_MACOS:
        assert hotkey_backend.normalize("Ctrl+Alt+2") == "Ctrl+Alt+2"
        return

    assert hotkey_backend.normalize("⌃⌥2") == "Ctrl+Alt+2"
    assert hotkey_backend.normalize("⌃⌥⇧C") == "Ctrl+Alt+Shift+C"
    # quem já está na notação passa intacto
    assert hotkey_backend.normalize("Ctrl+Alt+2") == "Ctrl+Alt+2"
    assert hotkey_backend.normalize("F2") == "F2"
    hotkey_backend.validate(hotkey_backend.normalize("⌃⌥2"))


def test_tecla_de_funcao_sozinha_e_valida():
    """"F2" solto sempre funcionou no Windows; o macOS não pode ser mais restrito.

    Exigir modificador para tudo era uma regra que eu inventei, e que criava
    diferença entre os dois sistemas — justamente no atalho de contador mais
    comum.
    """
    hotkey_backend.validate("F2")
    hotkey_backend.validate("Ctrl+Alt+2")


def test_letra_sozinha_continua_recusada():
    """No macOS, registrar "M" global capturaria a tecla no sistema inteiro.

    É uma regra do backend nativo, não do app: no Windows o pacote `keyboard`
    sempre aceitou letra sozinha, e mudar isso lá seria alterar comportamento
    que já existia.
    """
    import pytest

    if not hotkey_backend._ON_MACOS:
        return

    with pytest.raises(Exception):
        hotkey_backend.validate("M")


def test_float_above_fullscreen_nao_derruba_sem_janela_cocoa():
    """Sem plataforma Cocoa a função tem que desistir, não segfaultar.

    O winId() sob "offscreen" não aponta para um NSView; entregar esse ponteiro
    ao objc mata o processo com SIGSEGV. O smoke test do CI roda offscreen, e
    foi exatamente onde isso apareceu.
    """
    from streamer_sidekick.core.platform_utils import float_above_fullscreen

    class _FalsoWidget:
        def winId(self):
            return 0

    assert float_above_fullscreen(_FalsoWidget()) is False
    assert float_above_fullscreen(object()) is False


def test_float_above_fullscreen_limpa_a_bit_conflitante():
    """`MoveToActiveSpace` tem que ser limpo, não sobreposto.

    O macOS recusa essa bit junto com `CanJoinAllSpaces` e lança
    NSInternalInconsistencyException. Como o Qt a marca em janelas com pai, o
    `|` sem limpar fazia a configuração inteira falhar — e a janela do marcador
    simplesmente não aparecia sobre o jogo em tela cheia. Um `except` silencioso
    escondeu isso por uma versão inteira.
    """
    import sys

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QDialog

    from streamer_sidekick.core.platform_utils import float_above_fullscreen

    _app_qt()
    if sys.platform != "darwin" or QGuiApplication.platformName() != "cocoa":
        return  # sem janela Cocoa não há o que verificar

    import objc

    dlg = QDialog(None, Qt.WindowType.Tool)
    dlg.show()
    assert float_above_fullscreen(dlg) is True

    janela = objc.objc_object(c_void_p=int(dlg.winId())).window()
    comportamento = janela.collectionBehavior()
    assert comportamento & (1 << 0), "faltou CanJoinAllSpaces"
    assert not comportamento & (1 << 1), "MoveToActiveSpace continuou ligado"
    assert comportamento & (1 << 8), "faltou FullScreenAuxiliary"
    # nível baixo fica atrás de um app em tela cheia
    assert janela.level() >= 101
    dlg.close()


# --- Favoritos do Início ----------------------------------------------------


def test_favoritos_nunca_pedem_mais_largura_do_que_existe():
    """O quarto favorito sumia à direita, sem barra para alcançá-lo.

    A página rola só na vertical (ScrollBarAlwaysOff no eixo X), então tudo o
    que passa da viewport é cortado de vez. Quatro cards numa linha só pedem
    ~1124px; numa janela de 1000 o quarto simplesmente não existia para o
    usuário. Aqui trava o invariante: o que a grade pede sempre cabe.
    """
    from streamer_sidekick.ui.hub_window import MAX_FAVORITOS, favorite_columns

    largura, espaco = 260, 16
    for disponivel in range(0, 2000, 7):
        colunas = favorite_columns(disponivel, largura, espaco)
        assert 1 <= colunas <= MAX_FAVORITOS
        if colunas > 1:
            pedido = colunas * largura + (colunas - 1) * espaco
            assert pedido <= disponivel, (
                f"{colunas} colunas pedem {pedido}px e só há {disponivel}px"
            )


def test_favoritos_aproveitam_a_largura_quando_ela_existe():
    """O contrário também importa: numa tela larga os quatro têm de caber."""
    from streamer_sidekick.ui.hub_window import favorite_columns

    assert favorite_columns(4 * 260 + 3 * 16, 260, 16) == 4
    assert favorite_columns(3 * 260 + 2 * 16, 260, 16) == 3
    assert favorite_columns(2 * 260 + 16, 260, 16) == 2
    assert favorite_columns(100, 260, 16) == 1  # nunca zero: um card cortado
    assert favorite_columns(0, 260, 16) == 1
