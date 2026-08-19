# Como lançar uma versão

O build e a publicação da Release são **automáticos** via GitHub Actions
(`.github/workflows/release.yml`). Você só precisa bumpar a versão e criar a tag.

## Fluxo (GitFlow)

1. **Trabalhe na `develop`.** Feature/fix + testes (`pytest`).

2. **Bump da versão** (na `develop`). A fonte da verdade é
   `src/streamer_sidekick/__init__.py`; mantenha os outros em sincronia:
   - `src/streamer_sidekick/__init__.py` → `__version__`
   - `pyproject.toml` → `version`
   - `packaging/inno/streamer_sidekick.iss` → `MyAppVersion`
   - `packaging/streamer_sidekick_macos.spec` → `CFBundle*`
   - `app_release.json` → `version` **e** `zip_url` (aponta para a tag `vX.Y.Z`)

   > `scripts/package_portable.ps1` lê a versão do `__init__.py` — o nome do zip
   > sai automático.

3. **PR `develop` → `main`** e faça o merge (**Create a merge commit**).

   **É só isso.** Ao entrar na `main`, o workflow **Release** roda sozinho: lê a
   versão do código e, se ainda **não existir** uma Release para ela, roda os
   testes, builda o portable e **publica a Release já com o zip e a tag
   `vX.Y.Z`** — sem você criar tag na mão. Se a Release já existir (ex.: um commit
   na main que não mudou a versão), ele não faz nada.

   > Ou seja: **bump → PR → merge**. A tag e a publicação são automáticas.
   > (Não esqueça de bumpar a versão no passo 2, senão a Release nova não sai.)

## Sobre o auto-update (ordem importa)

O `app_release.json` da `main` é o que os apps instalados consultam. Como ele já
vai bumpado no PR do passo 2, **existe uma janela de ~3-5 min** entre o push da
tag e o CI publicar o asset — nesse intervalo um app que checar update pega 404
(falha graciosa). Para um projeto pequeno, tudo bem. Se quiser janela zero,
bumpe o `app_release.json` num commit separado **depois** que a Release estiver
publicada.

## CI

Todo push/PR em `main`/`develop` dispara `.github/workflows/ci.yml` (compila +
roda os testes). Não mergeie com o CI vermelho.
