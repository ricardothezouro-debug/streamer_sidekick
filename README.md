<p align="center">
  <img src="docs/home.png" alt="Streamer Sidekick" width="860">
</p>

<h1 align="center">Streamer Sidekick</h1>

<p align="center">
  Um hub desktop de ferramentas rápidas para a sua live — com sistema de plugins e guias de platina.
</p>

<p align="center">
  <a href="https://github.com/ricardothezouro-debug/streamer_sidekick/releases/latest"><b>⬇️ Baixar (Windows)</b></a>
  &nbsp;·&nbsp;
  <a href="PLUGIN_STANDARD.md">Criar plugins</a>
  &nbsp;·&nbsp;
  <a href="GUIA_DE_PLATINA.md">Criar guias de platina</a>
</p>

---

## ✨ Destaques

- 🧩 **Plugins** — marketplace dentro do app: instale ferramentas direto do GitHub, com um clique.
- 🏆 **Platinas** — guias de platina por jogo (checklist, dicas, imagens e progresso salvo), com busca.
- ⬆️ **Auto-update** — o app se atualiza sozinho, com barra de progresso neon, sem janelas feias.
- 🎯 **Marcador & Contador** — anote eventos da live com horário e monte overlays transparentes pro OBS.
- ⌨️ **Hotkeys globais** — funcionam mesmo com o jogo em foco, com detecção de conflito.

## 📸 Telas

**Platinas — marketplace curado de guias**

<img src="docs/platinas.png" alt="Aba Platinas" width="860">

**Um guia aberto (DREDGE) — direto no hub**

<img src="docs/guide.png" alt="Guia de platina do DREDGE" width="860">

**Sobre**

<img src="docs/about.png" alt="Tela Sobre" width="860">

## ⬇️ Baixar (Windows)

**➡️ [Baixe a versão mais recente na página de Releases](https://github.com/ricardothezouro-debug/streamer_sidekick/releases/latest)**

Baixe o `StreamerSidekick-*-portable.zip`, **extraia a pasta inteira** e execute o
`StreamerSidekick.exe`. Não precisa instalar nada — e o app se atualiza sozinho
quando sair uma versão nova.

> Suporte a macOS/Linux existe no código, mas é experimental e ainda não foi
> validado/lançado — será retomado no futuro.

## 🧩 Plugins

Na seção **Plugins** há um card **"+"** que abre o marketplace: os plugins vêm de
um catálogo curado (`plugins.json`) e são baixados direto do GitHub. Um plugin é
um repositório que expõe `module_info()` + `build_page()`.

Quer criar um? O padrão completo está em **[PLUGIN_STANDARD.md](PLUGIN_STANDARD.md)** —
feito para você (ou uma IA) seguir.

## 🏆 Platinas

A aba **Platinas** é um marketplace curado de **guias de platina por jogo**: cada
guia é um plugin (categoria `platina`) com checklist de troféus, dicas, imagens e
progresso salvo. Pesquise, instale e acompanhe seus troféus.

Para criar um guia, entregue a uma IA o **[GUIA_DE_PLATINA.md](GUIA_DE_PLATINA.md)**
(+ o `PLUGIN_STANDARD.md`) com os troféus do jogo — ela gera o guia completo.

## 🛠️ Para desenvolvedores

Rodar do código-fonte:

```powershell
.\.venv\Scripts\activate
python -m streamer_sidekick
```

Testes:

```bash
pip install -r requirements-dev.txt
pytest -q
```

Build do portable (também roda automático via GitHub Actions ao lançar):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_exe.ps1
.\scripts\package_portable.ps1
```

O fluxo de release está em **[RELEASING.md](RELEASING.md)** — na prática: bump da
versão → PR para `main` → o CI builda e publica a Release sozinho.

## 📄 Licença

Streamer Sidekick é licenciado sob a **PolyForm Noncommercial License 1.0.0** —
livre para uso pessoal e não comercial. Revenda, redistribuição paga ou venda de
versões modificadas exigem permissão por escrito. Veja `LICENSE` e `NOTICE`.
