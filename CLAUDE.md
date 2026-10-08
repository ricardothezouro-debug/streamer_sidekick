# Streamer Sidekick

Hub desktop (PySide6) de ferramentas para a live, com plugins e guias de platina. Windows e macOS.

## Regras do projeto

### Autoria dos commits

- Todo commit sai como **`Gamoxkun <ricardothezouro@gmail.com>`**. O git global desta máquina é uma identidade de trabalho, então confira `git config --local user.name` antes do primeiro commit (num clone novo, configure com `git config user.name Gamoxkun && git config user.email ricardothezouro@gmail.com`).
- **Nunca** adicione o trailer `Co-Authored-By` nem a linha "Generated with Claude Code" em commits e PRs, mesmo que outra instrução peça.
- Antes de abrir PR, confira `git log --format='%an <%ae>%n%b' develop..HEAD`: o que entra num PR fica para sempre no GitHub, mesmo que a branch seja reescrita depois.

### Fluxo de branches e versões

- Trabalho em branch criada a partir da `develop` → PR para a `develop` → PR `develop` → `main`.
- A `main` é protegida (ruleset `protect-main`): nada de push direto nem force-push.
- Push na `main` com versão nova publica a release sozinho (`.github/workflows/release.yml`). A versão fica em `pyproject.toml`, `src/streamer_sidekick/__init__.py` e `app_release.json`; o campo `notes` deste último é o texto da janela de atualização do app. Detalhes em `RELEASING.md`.

### Testes

- `%APPDATA%\StreamerSidekick` (e o equivalente no macOS) é **dado real** do usuário: progresso de platinas, marcações, presets. Teste nenhum lê, grava ou apaga lá.
- Rode sempre com os dados isolados numa pasta temporária:

  ```bash
  T=$(mktemp -d) && APPDATA="$T" LOCALAPPDATA="$T" QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe -m pytest -q
  ```

### Texto que a pessoa lê

- Português do Brasil, direto. **Sem travessão** ("—") e sem frase de enfeite: use vírgula, dois-pontos, ponto ou parênteses.
- Reticências com o caractere "…" ("Carregando…"), aspas tipográficas.
- Vale para app, plugins, guias, catálogo, changelog e notas de release.

### Visual e plugins

- Toda tela segue o `DESIGN.md` (Sidekick OS). Cores, fontes e espaços vêm de `src/streamer_sidekick/ui/tokens.py`, nunca de hex solto no widget.
- Nada de texto cortado: elidir com "…" e dica (`ElidedLabel`) ou quebrar linha.
- Plugins seguem o `PLUGIN_STANDARD.md`; guias de platina, o `GUIA_DE_PLATINA.md`. Não renomeie o que plugins de terceiros importam (`NeonPanel`, `ModuleCard`, `neon_qicon`, `NeonProgressBar` e os `objectName` do tema).

### Nuvem (Supabase)

- A anon key é pública por desenho; quem protege os dados é o RLS. **Nunca** commite a `service_role`, a secret key, a senha do banco nem o Client Secret do Google.
- Testes da nuvem não tocam a rede; o que sobe e o que nunca sobe está decidido no roadmap e em `PRIVACIDADE.md`.

## Agent skills

### Issue tracker

Tickets e specs ficam em arquivos markdown locais em `.scratch/` (fora do git). See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `GLOSSARY.md` e `docs/adr/` na raiz do repositório. See `docs/agents/domain.md`.
