# Streamer Sidekick

Streamer Sidekick is a Python desktop hub for stream helper tools.

## ⬇️ Baixar (Windows)

**➡️ [Baixe a versão mais recente na página de Releases](https://github.com/ricardothezouro-debug/streamer_sidekick/releases/latest)**

Baixe o arquivo `StreamerSidekick-*-portable.zip`, **extraia a pasta inteira** e
execute o `StreamerSidekick.exe`. Não precisa instalar nada — e o app se atualiza
sozinho quando sair uma versão nova.

Todas as versões (incluindo as anteriores) ficam em
**[Releases](https://github.com/ricardothezouro-debug/streamer_sidekick/releases)**.

## License

Streamer Sidekick is licensed under the PolyForm Noncommercial License
1.0.0. It is free for personal and non-commercial use.

Commercial resale, paid redistribution, or selling modified versions
requires written permission from the copyright holder. See `LICENSE` and
`NOTICE`.

Current modules:

- Marker: fast timestamped notes for gameplay and live events.
- Counter: OBS-friendly counter overlays and presets.

Initial goals:

- One modern PySide6 hub.
- Central config in the user app data folder.
- Central hotkey registry with conflict checks.
- Modular structure for future streamer tools.

## Plugins

O hub tem um sistema de plugins instalaveis. Na secao **Plugins** ha um card
**"+"** que abre o marketplace: os plugins disponiveis vem de um catalogo
(`plugins.json`, buscado remotamente do repositorio, com fallback embutido em
`assets/plugins_catalog.json`). Ao clicar em **Instalar**, o plugin e baixado
direto do GitHub como `.zip` (sem precisar de `git`), extraido para
`<app_data>/plugins/<id>/` e carregado no hub na hora.

Um plugin e um repositorio que expoe, em um modulo, o contrato:

```python
def module_info() -> ModuleInfo: ...      # dados do card
def build_page(config=None) -> QWidget: ...  # pagina embutida no hub
```

Cada plugin instalado guarda sua versao; quando o catalogo anuncia uma versao
mais nova, o card "+" mostra um aviso de **atualizacao disponivel**.

Para adicionar um plugin ao catalogo, basta editar `plugins.json` no repositorio
— nenhuma nova versao do app e necessaria. Cada plugin traz seu proprio icone
(PNG) e uma `version`; quando o catalogo anuncia uma versao mais nova, o card "+"
mostra o aviso e o marketplace exibe o **changelog**. Ao atualizar, a pagina do
plugin e recarregada **sem reiniciar** o app.

Quer criar um plugin? O padrao completo (contrato, manifesto, icone, design
system e regras) esta em **[PLUGIN_STANDARD.md](PLUGIN_STANDARD.md)** — um
arquivo pensado para ser entregue a uma IA junto da ideia do plugin.

> Seguranca: instalar um plugin baixa e executa codigo Python. O catalogo e
> curado: so aparecem no "+" os repositorios listados no `plugins.json`.

## Atualizacao do app

O proprio Streamer Sidekick se atualiza. A versao portable (Windows) verifica um
manifesto remoto (`app_release.json`) ao abrir e, se houver versao nova, mostra o
que mudou e oferece **Atualizar agora** — baixa, troca os arquivos e reabre
sozinho. Tambem da para checar manualmente na tela **Sobre**. Rodando do codigo,
a atualizacao e via `git pull`.

## Platforms

**Plataforma suportada hoje: Windows** (é onde as releases são publicadas e
testadas). O suporte a **macOS/Linux existe no código, mas é experimental** e
ainda não foi validado/lançado — será retomado no futuro.

A camada de atalhos globais escolhe o backend certo por sistema:

- Windows: pacote `keyboard`.
- macOS / Linux: pacote `pynput`.

No **macOS** os atalhos globais exigem que o app receba permissao em
`Ajustes do Sistema > Privacidade e Seguranca > Acessibilidade`. Sem essa
permissao a interface funciona, mas os atalhos globais nao disparam.

Os dados do app ficam em:

- Windows: `%APPDATA%\StreamerSidekick`
- macOS: `~/Library/Application Support/StreamerSidekick`
- Linux: `~/.config/StreamerSidekick`

Run during development (Windows):

```powershell
.\.venv\Scripts\activate
python -m streamer_sidekick
```

Run during development (macOS / Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamer_sidekick
```

Build the Windows executable:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_exe.ps1
```

The executable is generated at:

```text
dist\StreamerSidekick\StreamerSidekick.exe
```

Create a portable release zip:

```powershell
.\scripts\package_portable.ps1
```

Create a Windows installer after installing Inno Setup:

```powershell
.\scripts\build_installer.ps1
```

Build the macOS app bundle (run on a Mac):

```bash
pip install -r requirements-build.txt
chmod +x scripts/build_app_macos.sh
./scripts/build_app_macos.sh
```

The bundle is generated at `dist/Streamer Sidekick.app`.
