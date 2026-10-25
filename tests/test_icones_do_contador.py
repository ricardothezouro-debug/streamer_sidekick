"""Ícones do contador numa pasta do app (ticket 06; decisões Q31, Q32 e Q33)."""
import json
import os

import pytest


@pytest.fixture(scope="module", autouse=True)
def _app():
    from PySide6.QtWidgets import QApplication

    yield QApplication.instance() or QApplication([])


def _imagem(caminho, largura, altura, ruido=False):
    """PNG de verdade; com ruído ele não comprime e passa fácil de 1 MB."""
    from PySide6.QtGui import QColor, QImage

    if ruido:
        dados = os.urandom(largura * altura * 3)
        imagem = QImage(dados, largura, altura, largura * 3, QImage.Format.Format_RGB888).copy()
    else:
        imagem = QImage(largura, altura, QImage.Format.Format_RGB888)
        imagem.fill(QColor(200, 30, 30))
    assert imagem.save(str(caminho), "PNG")
    return caminho


def _icones(tmp_path):
    from streamer_sidekick.modules.counter.icons import CounterIcons

    return CounterIcons(tmp_path / "counter_icons")


def test_imagem_pequena_e_copiada_como_esta_e_o_nome_ganha_o_hash(tmp_path):
    original = _imagem(tmp_path / "Moeda.png", 64, 64)
    icones = _icones(tmp_path)

    nome = icones.import_image(original)

    assert nome.startswith("Moeda-") and nome.endswith(".png") and len(nome) == len("Moeda-12345678.png")
    assert icones.path_for(nome).read_bytes() == original.read_bytes()
    assert icones.path_for(nome).parent == tmp_path / "counter_icons"


def test_a_mesma_imagem_duas_vezes_vira_um_arquivo_so(tmp_path):
    original = _imagem(tmp_path / "moeda.png", 64, 64)
    icones = _icones(tmp_path)

    assert icones.import_image(original) == icones.import_image(original)
    assert len(list((tmp_path / "counter_icons").iterdir())) == 1


def test_dois_arquivos_com_o_mesmo_nome_nao_se_sobrescrevem(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    icones = _icones(tmp_path)

    um = icones.import_image(_imagem(tmp_path / "a" / "icon.png", 64, 64))
    outro = icones.import_image(_imagem(tmp_path / "b" / "icon.png", 32, 32))

    assert um != outro and icones.path_for(um).exists() and icones.path_for(outro).exists()


def test_imagem_acima_de_1_mb_vira_png_de_512_no_lado_maior(tmp_path):
    from PySide6.QtGui import QImage

    original = _imagem(tmp_path / "foto.png", 1200, 800, ruido=True)
    assert original.stat().st_size > 1024 * 1024

    nome = _icones(tmp_path).import_image(original)

    convertida = QImage(str(tmp_path / "counter_icons" / nome))
    assert nome.endswith(".png") and (convertida.width(), convertida.height()) == (512, 341)


def test_imagem_grande_que_nao_da_para_ler_avisa(tmp_path):
    from streamer_sidekick.modules.counter.icons import IconError

    lixo = tmp_path / "quebrada.png"
    lixo.write_bytes(os.urandom(1024 * 1024 + 10))

    with pytest.raises(IconError):
        _icones(tmp_path).import_image(lixo)
    assert not (tmp_path / "counter_icons").exists() or not any((tmp_path / "counter_icons").iterdir())


def test_nome_que_nao_existe_ou_aponta_para_fora_nao_resolve(tmp_path):
    icones = _icones(tmp_path)

    assert icones.path_for("sumiu-12345678.png") is None
    assert icones.path_for("../config.json") is None
    assert icones.path_for("") is None


def _servico(tmp_path):
    from streamer_sidekick.core.config import ConfigStore
    from streamer_sidekick.modules.counter.icons import CounterIcons
    from streamer_sidekick.modules.counter.service import CounterService

    config = ConfigStore(path=tmp_path / "config.json")
    config.set("counter.presets_folder", str(tmp_path / "presets"))
    return CounterService(config, icons=CounterIcons(tmp_path / "counter_icons"))


def _preset_antigo(tmp_path, nome, icone):
    (tmp_path / "presets").mkdir(exist_ok=True)
    preset = tmp_path / "presets" / f"{nome}.json"
    preset.write_text(json.dumps([{"titulo": "Mortes", "hotkey": "ctrl+1", "icone": icone, "icon_size": 40}]),
                      encoding="utf-8")
    return preset


def test_preset_antigo_com_caminho_absoluto_migra_para_o_nome_uma_vez(tmp_path):
    imagem = _imagem(tmp_path / "caveira.png", 64, 64)
    preset = _preset_antigo(tmp_path, "dredge", str(imagem.resolve()))
    servico = _servico(tmp_path)

    contador = servico.load_preset(preset)[0]

    nome = contador["icone"]
    assert nome.startswith("caveira-") and "/" not in nome and "\\" not in nome
    assert servico.icons.path_for(nome).read_bytes() == imagem.read_bytes()
    assert json.loads(preset.read_text(encoding="utf-8"))[0]["icone"] == nome, "o preset fica migrado no disco"
    assert contador["titulo"] == "Mortes" and contador["hotkey"] == "ctrl+1" and contador["icon_size"] == 40

    antes = preset.read_bytes()
    assert servico.load_preset(preset)[0]["icone"] == nome
    assert preset.read_bytes() == antes and len(list((tmp_path / "counter_icons").iterdir())) == 1


def test_imagem_original_apagada_deixa_o_icone_vazio_e_o_preset_funciona(tmp_path):
    preset = _preset_antigo(tmp_path, "dredge", str(tmp_path / "nao-existe" / "caveira.png"))

    contador = _servico(tmp_path).load_preset(preset)[0]

    assert contador["icone"] is None and contador["titulo"] == "Mortes"
    assert json.loads(preset.read_text(encoding="utf-8"))[0]["icone"] is None


def test_ao_abrir_o_app_todos_os_presets_sao_migrados(tmp_path):
    imagem = _imagem(tmp_path / "caveira.png", 64, 64)
    um = _preset_antigo(tmp_path, "dredge", str(imagem.resolve()))
    outro = _preset_antigo(tmp_path, "elden", str(imagem.resolve()))
    (tmp_path / "presets" / "quebrado.json").write_text("{nao é json", encoding="utf-8")

    _servico(tmp_path).migrate_icons()

    nomes = {json.loads(p.read_text(encoding="utf-8"))[0]["icone"] for p in (um, outro)}
    assert len(nomes) == 1 and next(iter(nomes)).startswith("caveira-"), "a mesma imagem, uma cópia só"


def test_overlay_mostra_a_imagem_do_nome_guardado_no_preset(tmp_path, monkeypatch):
    import streamer_sidekick.core.hotkey_backend as hk
    from streamer_sidekick.modules.counter.overlay import CounterOverlay
    from streamer_sidekick.modules.counter.service import default_counter_config

    monkeypatch.setattr(hk, "register", lambda *a, **k: None)  # nada de atalho global no PC
    icones = _icones(tmp_path)
    nome = icones.import_image(_imagem(tmp_path / "caveira.png", 64, 64))
    config = dict(default_counter_config(), icone=nome, icon_size=40)

    overlay = CounterOverlay(config, tmp_path / "dredge_state.json", 0, icons=icones)
    try:
        assert f'src="{icones.path_for(nome).as_posix()}"' in overlay.label.text()
        assert 'height="40"' in overlay.label.text()
    finally:
        overlay.deleteLater()


def test_overlay_com_icone_que_nao_existe_mostra_so_o_numero(tmp_path, monkeypatch):
    import streamer_sidekick.core.hotkey_backend as hk
    from streamer_sidekick.modules.counter.overlay import CounterOverlay
    from streamer_sidekick.modules.counter.service import default_counter_config

    monkeypatch.setattr(hk, "register", lambda *a, **k: None)
    config = dict(default_counter_config(), icone="sumiu-12345678.png")

    overlay = CounterOverlay(config, tmp_path / "dredge_state.json", 0, icons=_icones(tmp_path))
    try:
        assert "<img" not in overlay.label.text() and ">0<" in overlay.label.text()
    finally:
        overlay.deleteLater()


def test_escolher_o_icone_no_editor_copia_para_a_pasta_e_guarda_so_o_nome(tmp_path, monkeypatch):
    import streamer_sidekick.ui.counter_editor as editor

    original = _imagem(tmp_path / "caveira.png", 64, 64)
    monkeypatch.setattr(editor.QFileDialog, "getOpenFileName", lambda *a, **k: (str(original), ""))
    icones = _icones(tmp_path)
    dialogo = editor.CounterPresetDialog(preset_name="dredge", icons=icones)
    try:
        dialogo.forms[0]._choose_icon()

        nome = dialogo.counter_configs()[0]["icone"]
        assert nome.startswith("caveira-") and icones.path_for(nome) is not None
        assert icones.path_for(nome).as_posix() in dialogo.forms[0].preview.text()
    finally:
        dialogo.deleteLater()


def test_imagem_que_nao_da_para_usar_avisa_no_editor_e_fica_sem_icone(tmp_path, monkeypatch):
    import streamer_sidekick.ui.counter_editor as editor

    lixo = tmp_path / "quebrada.png"
    lixo.write_bytes(os.urandom(1024 * 1024 + 10))
    avisos = []
    monkeypatch.setattr(editor.QFileDialog, "getOpenFileName", lambda *a, **k: (str(lixo), ""))
    monkeypatch.setattr(editor.QMessageBox, "warning", lambda _pai, _titulo, texto: avisos.append(texto))
    dialogo = editor.CounterPresetDialog(preset_name="dredge", icons=_icones(tmp_path))
    try:
        dialogo.forms[0]._choose_icon()

        assert dialogo.counter_configs()[0]["icone"] is None
        assert avisos and avisos[0].startswith("Não deu para usar essa imagem")
    finally:
        dialogo.deleteLater()


def test_backup_em_zip_leva_e_traz_a_pasta_de_icones(tmp_path):
    import zipfile

    from streamer_sidekick.core.backup import BackupService
    from streamer_sidekick.modules.marker.service import MarkerService

    servico = _servico(tmp_path)
    servico.config.set("marker.folder", str(tmp_path / "markers"))
    nome = servico.icons.import_image(_imagem(tmp_path / "caveira.png", 64, 64))
    copia = servico.icons.path_for(nome).read_bytes()
    backup = BackupService(servico.config, MarkerService(servico.config), servico)

    arquivo = tmp_path / "backup.zip"
    backup.export_backup(arquivo)
    assert f"counter_icons/{nome}" in zipfile.ZipFile(arquivo).namelist()

    servico.icons.path_for(nome).unlink()
    backup.restore_backup(arquivo)
    assert servico.icons.path_for(nome).read_bytes() == copia
