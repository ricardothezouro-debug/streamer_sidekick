# Padrão de Plugin do Streamer Sidekick

Este documento é a especificação completa para criar um plugin do **Streamer
Sidekick**. Ele é autocontido: entregue este arquivo a uma IA (ou a um dev) junto
da ideia do plugin e ela terá tudo para produzir algo que instala, aparece no hub
e combina visualmente com o app.

> **TL;DR** — Um plugin é um repositório público no GitHub, em Python + PySide6,
> que expõe um módulo com `module_info()` e `build_page()`. O Sidekick baixa o
> repositório como `.zip`, importa esse módulo e embute a página no hub. O plugin
> é anunciado no catálogo `plugins.json` do Sidekick.

---

## 1. Como o Sidekick carrega um plugin

1. O usuário abre o hub → seção **Plugins** → card **"+"** → escolhe um plugin.
2. O Sidekick baixa o repositório do GitHub como `.zip` (branch do catálogo),
   extrai para `<dados-do-app>/plugins/<id>/` e grava um `plugin.json` (manifesto).
3. Adiciona `<pasta-do-plugin>/<src_subdir>` ao `sys.path` e importa o módulo
   declarado (ex.: `meu_plugin.module`).
4. Chama `module_info()` para montar o **card** e `build_page()` para montar a
   **página** embutida no `QStackedWidget` do hub.

Os dados do usuário do próprio plugin devem ficar em `%APPDATA%` (Windows) /
`~/Library/Application Support` (macOS) / `~/.config` (Linux) — **nunca** dentro da
pasta do plugin (ela é sobrescrita em atualizações).

---

## 2. O contrato (obrigatório)

O módulo declarado no manifesto (`module`) **precisa** expor estas duas funções:

```python
def module_info():
    """Metadados do card. Deve devolver um objeto com estes atributos:
       module_id, title, subtitle, status, accent  (e, opcional, icon).
    Use a classe ModuleInfo do Sidekick quando ela estiver importável, senão
    uma cópia local compatível (assim o plugin roda standalone também)."""

def build_page(config=None):
    """Devolve um QWidget (PySide6) pronto para ser inserido no hub.
    - Se config for None, o plugin cria a própria configuração.
    - NÃO faça trabalho pesado/bloqueante aqui nem no import do módulo.
    - O tema é global (QApplication), então a página já herda o visual."""
```

### Opcional: `help_text()`

Se o módulo expuser `help_text() -> str`, o Sidekick mostra esse texto na tela
**Ajuda**, numa seção com o nome e o ícone do plugin (aparece automaticamente
quando o plugin é instalado). Use texto simples com quebras de linha (`\n`).

```python
def help_text() -> str:
    return (
        "O que o plugin faz, em uma frase.\n\n"
        "Como usar:\n"
        "• Passo 1...\n"
        "• Passo 2..."
    )
```

### Campos de `module_info()`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `module_id` | str | Igual ao `id` do plugin no catálogo (ex.: `"launcher"`). |
| `title` | str | Nome exibido no card e na navegação. Curto. |
| `subtitle` | str | Uma linha explicando o que faz. |
| `status` | str | Texto curto de estado (ex.: `"Pronto"`). |
| `accent` | str | Cor de destaque em hex (ver paleta). |
| `icon` | str | *(opcional)* usado pelo Sidekick, não pelo plugin — ver §5. |

Exemplo de `module_info()` resiliente (funciona dentro e fora do Sidekick):

```python
from dataclasses import dataclass

ACCENT = "#37F2FF"
MODULE_ID = "meu_plugin"

@dataclass(frozen=True)
class ModuleInfo:
    module_id: str; title: str; subtitle: str; status: str; accent: str

def module_info():
    data = dict(module_id=MODULE_ID, title="Meu Plugin",
                subtitle="O que ele faz em uma linha.",
                status="Pronto", accent=ACCENT)
    try:
        from streamer_sidekick.core.modules import ModuleInfo as SK
        return SK(**data)
    except Exception:
        return ModuleInfo(**data)
```

---

## 3. Estrutura do repositório

```
meu-plugin/                      (repositório no GitHub)
  src/
    meu_plugin/
      __init__.py
      module.py                  <- expõe module_info() e build_page()
      core/                      (config, lógica…)
      ui/                        (páginas, widgets…)
      assets/brand/icon.png      <- ícone do card (ver §5)
  requirements.txt               (só PySide6, idealmente — ver §7)
  README.md
```

O `src_subdir` (normalmente `src`) é o que entra no `sys.path`; o `module` é o
caminho de import a partir dele (ex.: `meu_plugin.module`).

---

## 4. Entrada no catálogo (`plugins.json`)

Para o plugin aparecer no "+", adicione uma entrada ao `plugins.json` do
repositório do Sidekick:

```json
{
  "id": "meu_plugin",
  "name": "Meu Plugin",
  "description": "Descrição curta exibida no marketplace.",
  "repo": "seu-usuario/meu-plugin",
  "ref": "main",
  "version": "1.0.0",
  "src_subdir": "src",
  "module": "meu_plugin.module",
  "accent": "#37F2FF",
  "icon": "src/meu_plugin/assets/brand/icon.png",
  "changelog": "O que há de novo nesta versão."
}
```

| Campo | Obrigatório | Observação |
|-------|:---:|------------|
| `id` | sim | Único; igual a `module_id`. |
| `name` | sim | Nome no marketplace. |
| `description` | sim | Uma frase. |
| `repo` | sim | `owner/repo` do GitHub. |
| `ref` | não | Branch (padrão `main`). |
| `version` | sim | **SemVer** `MAJOR.MINOR.PATCH`. Controla o aviso de update. |
| `src_subdir` | não | Pasta que entra no `sys.path` (padrão `src`). |
| `module` | sim | Módulo de import com `module_info`/`build_page`. |
| `accent` | não | Cor de destaque (padrão `#37F2FF`). |
| `icon` | não | Caminho do PNG **relativo à raiz do repositório**. |
| `changelog` | não | Mostrado quando há atualização. |
| `min_sidekick_version` | não | Versão mínima do Sidekick (SemVer). Se o app for mais antigo, o "+" mostra **Incompatível** e não instala. |

Aumente `version` a cada release para disparar o selo de **atualização
disponível** e mostrar o `changelog`.

---

## 5. Ícone

- Formato **PNG** com fundo **transparente**, quadrado, ~256×256 px.
- Caminho declarado em `icon` (relativo à raiz do repo) e **versionado no Git**
  (se seu `.gitignore` ignora ícones gerados, destrave este).
- O Sidekick renderiza esse PNG no card e na navegação; sem ele, cai num ícone
  vetorial genérico.
- Estilo recomendado: traço neon em gradiente ciano→magenta sobre um quadrado
  arredondado escuro (combina com a identidade — ver paleta).

---

## 6. Design system (para a página combinar com o hub)

O tema é aplicado no `QApplication` inteiro, então **use `QWidget`/`QLabel`/
`QPushButton` padrão do PySide6** e nomeie os objetos (`setObjectName(...)`) para
herdar o estilo. Não defina cores fixas na mão quando um `objectName` já resolve.

### Paleta

| Nome | Hex | Uso |
|------|-----|-----|
| Void Black | `#0A0B12` | Fundo geral |
| Painel | `#0D121B` | Fundo de cards/painéis |
| Border | `#273140` | Bordas |
| Soft White | `#F3F6FF` | Texto principal |
| Muted | `#A8B0BC` | Texto secundário |
| **Electric Cyan** | `#37F2FF` | Destaque primário / foco |
| **Neon Magenta** | `#FF4FD8` | Destaque secundário |
| **Acid Lime** | `#B9FF43` | Sucesso / novidade |

### Tipografia

- Títulos: **Bahnschrift** (fallback do Windows; o app é portátil).
- Corpo: **Segoe UI**. Mono: **Consolas**.

### `objectName`s já estilizados (use-os)

| objectName | O que é |
|------------|---------|
| `PageTitle` | Título grande da página (38px). |
| `SectionTitle` | Título de seção (18px, bold). |
| `CardTitle` | Título de card (24px, Bahnschrift). |
| `Muted` | Texto secundário acinzentado. |
| `Kicker` | Numeração/etiqueta em ciano mono. |
| `StatusPill` | "Pílula" de status com borda. |
| `PrimaryButton` | Botão de ação principal (borda ciano). |
| `NeonPanel` | Card de canto cortado com borda em gradiente. |

Exemplo mínimo de página no padrão:

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton

class MinhaPagina(QWidget):
    def __init__(self, config):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 22, 0)
        layout.setSpacing(18)

        title = QLabel("Meu Plugin"); title.setObjectName("PageTitle")
        hint = QLabel("Explique aqui o que a página faz."); hint.setObjectName("Muted")
        hint.setWordWrap(True)
        action = QPushButton("Fazer algo"); action.setObjectName("PrimaryButton")

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(action)
        layout.addStretch(1)
```

Para o card de canto cortado com borda neon, reutilize o `NeonPanel` do Sidekick
quando importável, ou replique o visual (fundo `#0D121B`, borda em gradiente
ciano→magenta, cantos cortados).

---

## 7. Regras de funcionamento (importante)

1. **PySide6 apenas.** O Sidekick embarca o PySide6; se seu plugin importar QtCore/
   QtGui/QtWidgets, funciona inclusive no app empacotado (portable). **Evite
   dependências de terceiros** — no build congelado elas não existem e o import
   falha. Se precisar de algo além do PySide6 + stdlib, documente e saiba que só
   roda a partir do código-fonte, não do portable.
2. **Nada de bloquear.** Não faça rede, disco pesado ou `sleep` no import do módulo
   nem em `build_page()`. Trabalho demorado vai para uma `QThread` e reporta por
   `Signal`.
3. **Thread-safety.** Callbacks de threads/hotkeys devem voltar à thread da GUI via
   `Signal` antes de mexer em widgets.
4. **Configuração própria.** Guarde config/estado do plugin no diretório de dados do
   usuário do SO — não na pasta do plugin (sobrescrita em updates).
5. **Sem efeitos colaterais na importação.** Não abra janelas, não registre hotkeys
   globais nem inicie processos só por ser importado. Faça isso sob ação do usuário.
6. **Falhe suave.** Se algo der errado em `build_page()`, levante uma exceção clara
   (o hub isola e mostra uma página de erro em vez de cair).
7. **Não conflite hotkeys.** Se usar atalhos, deixe-os configuráveis.

---

## 8. Versionamento e atualização

- Use **SemVer**. O Sidekick compara `version` do catálogo com a instalada; se for
  maior, mostra **"Atualizar"** e o `changelog`.
- Ao atualizar, o Sidekick rebaixa o `.zip`, troca os arquivos e **recarrega a
  página do plugin sem reiniciar** o app.
- Mantenha compatibilidade da config entre versões (migre se mudar o formato).

---

## 9. Segurança

Instalar um plugin executa o código dele. Por isso o catálogo é **curado**: só
entram no "+" os repositórios listados no `plugins.json` do Sidekick. Publique só
repositórios confiáveis e mantenha-os sob seu controle.

---

## 10. Checklist de publicação

- [ ] Repositório público no GitHub, `src/<pacote>/module.py` com `module_info()` e `build_page()`.
- [ ] `module_info()` funciona com e sem o Sidekick importável.
- [ ] `build_page(config=None)` devolve um `QWidget`, sem trabalho pesado.
- [ ] *(Opcional)* `help_text()` com uma explicação para a tela Ajuda.
- [ ] Só PySide6/stdlib como dependência (ou documentado o contrário).
- [ ] Config/estado do usuário fora da pasta do plugin.
- [ ] `assets/brand/icon.png` (PNG transparente ~256px) **versionado**.
- [ ] Página usando os `objectName`s do design system.
- [ ] Entrada adicionada ao `plugins.json` do Sidekick com `version` SemVer.
- [ ] Testado: instalar pelo "+", abrir a página, e (ao subir a versão) atualizar.
```

---

*Referência viva: o plugin **StreamOn** (`ricardothezouro-debug/StreamOn`) segue
este padrão e serve de exemplo real — veja o `src/stream_ligar/module.py`.*
