---
version: alpha
name: sidekick-os
description: >-
  Streamer Sidekick é o "sistema operacional" de bolso de um streamer gamer, um hub
  desktop (Windows e macOS, PySide6) com ferramentas de live, plugins e guias de platina.
  A linguagem visual Sidekick OS junta a disciplina de um HUD escuro (fundo quase preto
  azulado, brilho só no que importa) com a memória de um SO retrô synthwave, feita de
  painéis-janela com barra de título em fonte VCR, sombra dura deslocada, números em
  display de terminal, progresso em blocos e a arte de sol listrado com grid em
  perspectiva reservada para momentos de marca. Ciano é a cor de ação, rosa é a marca e
  o "ao vivo", verde-limão é progresso e conquista. O documento cobre o hub, as páginas
  internas, o marketplace de plugins e a aba Platinas, e é a referência visual para
  plugins e guias de terceiros.

colors:
  canvas: "#120A24"
  sunken: "#0B0716"
  surface: "#161029"
  surface-raised: "#211839"
  hairline: "#352A54"
  hairline-strong: "#4B3E72"
  control-border: "#7465A0"
  ink: "#F4F0FF"
  ink-muted: "#BCB2DA"
  ink-faint: "#9388B6"
  primary: "#37F2FF"
  primary-hover: "#7AF6FF"
  on-primary: "#04131A"
  primary-tint: "#123B4A"
  brand: "#FF4FD8"
  on-brand: "#1A0414"
  success: "#B9FF43"
  on-success: "#0B1400"
  warning: "#FFC857"
  danger: "#FF5C7A"
  synth: "#7B3CFF"
  synth-sun-top: "#FFD35C"
  synth-sun-bottom: "#FF4FD8"
  shadow-hard: "#000000"

typography:
  display:     { fontFamily: Chakra Petch, fontSize: 32px, fontWeight: 700, lineHeight: 1.15 }
  heading:     { fontFamily: Chakra Petch, fontSize: 22px, fontWeight: 600, lineHeight: 1.25 }
  title:       { fontFamily: Chakra Petch, fontSize: 18px, fontWeight: 600, lineHeight: 1.30 }
  body:        { fontFamily: IBM Plex Sans, fontSize: 14px, fontWeight: 400, lineHeight: 1.50 }
  body-strong: { fontFamily: IBM Plex Sans, fontSize: 14px, fontWeight: 600, lineHeight: 1.50 }
  caption:     { fontFamily: IBM Plex Sans, fontSize: 12px, fontWeight: 400, lineHeight: 1.45 }
  button:      { fontFamily: IBM Plex Sans, fontSize: 13px, fontWeight: 600, lineHeight: 1.20 }
  hud-label:   { fontFamily: VT323, fontSize: 20px, fontWeight: 400, lineHeight: 1.00, letterSpacing: 1px }
  numeric-lg:  { fontFamily: VT323, fontSize: 44px, fontWeight: 400, lineHeight: 1.00 }
  numeric-md:  { fontFamily: VT323, fontSize: 24px, fontWeight: 400, lineHeight: 1.00 }
  mono:        { fontFamily: IBM Plex Mono, fontSize: 12px, fontWeight: 400, lineHeight: 1.45 }

rounded:
  none: 0px
  xs: 2px
  sm: 4px
  md: 6px
  full: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px

components:
  panel-window:
    backgroundColor: "{colors.surface}"
    border: "1px solid {colors.hairline}"
    rounded: "{rounded.sm}"
    chamfer: "10px no canto superior direito"
    shadow: "4px 4px 0 {colors.shadow-hard} a 70%"
    padding: "{spacing.md}"
  panel-window-titlebar:
    height: 30px
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.hud-label}"
    border: "0 0 1px 0 solid {colors.hairline}"
    padding: "0 {spacing.sm}"
  panel-window-featured:
    border: "1px solid {colors.primary}"
    accentStripe: "2px no topo da barra de título, {colors.brand}"
    glow: "0 0 16px {colors.primary} a 25%"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
    minHeight: 34px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-primary-pressed:
    backgroundColor: "{colors.primary}"
    offset: "1px para baixo"
  button-primary-disabled:
    backgroundColor: "{colors.hairline}"
    textColor: "{colors.ink-faint}"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    border: "1px solid {colors.hairline-strong}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
    minHeight: 34px
  button-secondary-hover:
    border: "1px solid {colors.primary}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.primary}"
    typography: "{typography.button}"
    padding: "8px 10px"
  button-danger:
    backgroundColor: "transparent"
    textColor: "{colors.danger}"
    border: "1px solid {colors.danger}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  input:
    backgroundColor: "{colors.sunken}"
    textColor: "{colors.ink}"
    placeholderColor: "{colors.ink-faint}"
    border: "1px solid {colors.control-border}"
    rounded: "{rounded.sm}"
    padding: "8px 10px"
    minHeight: 34px
  input-focus:
    border: "1px solid {colors.primary}"
  focus-ring:
    border: "2px solid {colors.primary}"
  nav-item:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    typography: "{typography.body-strong}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
  nav-item-hover:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
  nav-item-active:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    indicator: "barra de 3px à esquerda, {colors.brand}"
  tab:
    textColor: "{colors.ink-muted}"
    typography: "{typography.body-strong}"
    border: "0 0 2px 0 solid transparent"
    padding: "8px 12px"
  tab-active:
    textColor: "{colors.ink}"
    border: "0 0 2px 0 solid {colors.primary}"
  status-chip:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    padding: "3px 10px"
    dot: "8px, na cor semântica do estado"
  segmented-progress:
    segmentSize: "10px x 14px"
    gap: 3px
    fillColor: "{colors.success}"
    emptyColor: "{colors.hairline}"
    label: "{typography.numeric-md}"
  numeric-display:
    typography: "{typography.numeric-lg}"
    textColor: "{colors.ink}"
  module-card:
    backgroundColor: "{colors.surface}"
    border: "1px solid {colors.hairline}"
    rounded: "{rounded.sm}"
    padding: "{spacing.md}"
    iconBox: "56px, {colors.sunken}, {rounded.md}"
    icon: "icon-brand de 48px (ferramentas nativas) ou o ícone do próprio plugin"
  icon-ui:
    grid: "24 x 24"
    stroke: "2px reais (1,5px no tamanho 16), pontas quadradas, junções em quina"
    corner: "chanfro de 3 unidades no canto superior direito, como o panel-window"
    sizes: "24 (nav), 20 (subnav), 16 (dentro de botão e chip)"
    color: "{colors.ink-muted}"
  icon-ui-hover:
    color: "{colors.ink}"
  icon-ui-active:
    color: "{colors.primary}"
  icon-ui-destructive:
    color: "{colors.danger}"
  icon-ui-disabled:
    color: "{colors.ink-faint}"
  icon-brand:
    grid: "12 x 12 células sólidas, sem antisserrilhado"
    sizes: "48 (cards, telas vazias, conquistas) e 96 (onboarding); nunca abaixo de 48"
    inks: "cor do papel do ícone + 1 acento + {colors.ink} para brilho"
  module-card-hover:
    border: "1px solid {colors.hairline-strong}"
  callout-info:
    backgroundColor: "{colors.surface-raised}"
    border: "0 0 0 3px solid {colors.primary}"
    rounded: "{rounded.xs}"
    padding: "{spacing.sm} {spacing.md}"
  callout-warning:
    backgroundColor: "{colors.surface-raised}"
    border: "0 0 0 3px solid {colors.warning}"
    rounded: "{rounded.xs}"
    padding: "{spacing.sm} {spacing.md}"
  callout-danger:
    backgroundColor: "{colors.surface-raised}"
    border: "0 0 0 3px solid {colors.danger}"
    rounded: "{rounded.xs}"
    padding: "{spacing.sm} {spacing.md}"
  app-shell:
    backgroundColor: "{colors.canvas}"
    sidebarBackground: "{colors.sunken}"
    sidebarWidth: 232px
  list-item-selected:
    backgroundColor: "{colors.primary-tint}"
    textColor: "{colors.ink}"
  live-badge:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.on-brand}"
    typography: "{typography.hud-label}"
    rounded: "{rounded.xs}"
    padding: "2px 8px"
  trophy-badge:
    backgroundColor: "{colors.success}"
    textColor: "{colors.on-success}"
    typography: "{typography.hud-label}"
    rounded: "{rounded.xs}"
    padding: "2px 8px"
  tag-missable:
    backgroundColor: "transparent"
    textColor: "{colors.warning}"
    border: "1px solid {colors.warning}"
    typography: "{typography.hud-label}"
    rounded: "{rounded.xs}"
    padding: "1px 6px"
  tag-spoiler:
    backgroundColor: "transparent"
    textColor: "{colors.ink-muted}"
    border: "1px solid {colors.hairline-strong}"
    typography: "{typography.hud-label}"
    rounded: "{rounded.xs}"
    padding: "1px 6px"
  synth-hero:
    height: 140px
    sun: "gradiente {colors.synth-sun-top} → {colors.synth-sun-bottom}, 5 cortes horizontais"
    horizon: "{colors.synth} a 40%"
    grid: "linhas {colors.primary} a 35%, perspectiva com ponto de fuga central"
---

# Sidekick OS — design system do Streamer Sidekick

## Overview

O Streamer Sidekick é usado **durante a live**, com o jogo aberto e a atenção dividida. Por isso o sistema é escuro, calmo e previsível: a interface se apaga e só o que importa acende (a ação principal, o progresso, o "ao vivo"). A personalidade vem de outro lugar: da metáfora de um **SO retrô de gamer**. Cada bloco da tela é uma janela com barra de título, os números aparecem num display de terminal e o progresso das platinas avança em blocos, como uma barra de vida.

A estética synthwave/future funk (sol listrado, grid em perspectiva, roxo e magenta) é **tempero, não prato**. Ela aparece no papel de parede da área de conteúdo, no topo do Início, no onboarding, nas telas vazias e no Sobre. Texto nunca fica direto sobre a arte: fica sempre dentro de um painel opaco.

**Key Characteristics:**
- Neutros escuros tingidos de roxo em quatro níveis: `{colors.sunken}` < `{colors.canvas}` < `{colors.surface}` < `{colors.surface-raised}`.
- Painéis-janela (`panel-window`) com barra de título em `{typography.hud-label}`, canto superior direito chanfrado e sombra dura deslocada, sem desfoque.
- **Brilho é exceção:** só o painel em destaque, a barra de progresso e o indicador "ao vivo" podem brilhar. No máximo um painel em destaque por tela.
- Cores com papel fixo: ciano `{colors.primary}` = agir, rosa `{colors.brand}` = marca e ao vivo, limão `{colors.success}` = progresso e conquista.
- Três famílias de fonte embarcadas, iguais no Windows e no macOS: Chakra Petch (títulos), IBM Plex Sans (interface e texto) e VT323 (rótulos de HUD e números).
- Dois conjuntos de ícones: linha HUD (`icon-ui`) na interface e pixel-art 12×12 (`icon-brand`) nos momentos de marca. Nunca emoji, nunca degradê.

## Colors

### Brand & Accent

| Token | Papel | Use em | Não use em |
|---|---|---|---|
| `{colors.primary}` | Ação | botão primário, foco, aba ativa, links, painel em destaque | texto corrido, decoração |
| `{colors.brand}` | Marca e ao vivo | logo, indicador de nav ativa, "ao vivo/gravando", faixa do painel em destaque | botões, estados de erro |
| `{colors.success}` | Progresso e conquista | barra de progresso, troféu obtido, "concluído", "+" de adicionar plugin | texto longo, fundos grandes |
| `{colors.synth}` | Tinta synthwave | arte do `synth-hero`, onboarding, telas vazias | qualquer controle interativo |

`{colors.primary-tint}` é o fundo de destaque suave de ciano (item selecionado numa lista, linha ativa). `{colors.primary-hover}` existe só para o hover do botão primário.

### Surface

| Token | Uso |
|---|---|
| `{colors.sunken}` | barra lateral, campos de texto, poços (área de lista) |
| `{colors.canvas}` | fundo da janela; base do papel de parede "Liso" |
| `{colors.surface}` | corpo de painéis e cards |
| `{colors.surface-raised}` | barra de título, hover, chips, callouts, item de nav ativo |
| `{colors.hairline}` | divisórias e borda de painel |
| `{colors.hairline-strong}` | borda de botão secundário e hover de card |
| `{colors.control-border}` | borda de campos de formulário (3,6:1 sobre a superfície, acima do mínimo WCAG de 3:1 para componentes) |

### Text

| Token | Uso | Contraste sobre `surface` |
|---|---|---|
| `{colors.ink}` | texto principal e títulos | 16,4:1 |
| `{colors.ink-muted}` | texto secundário e descrições | 9,2:1 |
| `{colors.ink-faint}` | placeholder, desabilitado, metadados | 5,6:1 |

### Semantic

`{colors.success}` (ok), `{colors.warning}` (atenção), `{colors.danger}` (erro, destrutivo) e `{colors.primary}` (informação). Todos passam AA como texto sobre `{colors.surface}`. Estado nunca é comunicado só por cor: sempre há texto ou ícone junto (o ponto do `status-chip` acompanha um rótulo).

## Typography

### Font Family

- **Chakra Petch** (display, títulos): angular e técnica, dá o tom de "SO" sem virar ficção científica genérica. Substitui a Bahnschrift.
- **IBM Plex Sans** (interface, texto, botões): legível em tamanho pequeno e com acentos completos. Substitui a Segoe UI.
- **VT323** (HUD): fonte de terminal/VCR. Só para rótulos curtos em caixa alta e números.
- **IBM Plex Mono** (caminhos de arquivo, logs, atalhos de teclado). Substitui a Consolas.

As quatro são OFL e vão embarcadas em `src/streamer_sidekick/assets/fonts/`, registradas via `QFontDatabase`. Assim o app tem a mesma cara no Windows e no macOS.

### Hierarchy

| Papel | Token | Tamanho / peso | Uso |
|---|---|---|---|
| Título de página | `{typography.display}` | 32 / 700 | um por página |
| Seção | `{typography.heading}` | 22 / 600 | blocos dentro da página |
| Título de card | `{typography.title}` | 18 / 600 | cards, itens de lista, diálogos |
| Texto | `{typography.body}` | 14 / 400 | descrições, parágrafos |
| Texto forte | `{typography.body-strong}` | 14 / 600 | itens de nav, rótulos de campo |
| Legenda | `{typography.caption}` | 12 / 400 | metadados, chips, dicas |
| Botão | `{typography.button}` | 13 / 600 | todos os botões |
| HUD | `{typography.hud-label}` | 20 VT323, caixa alta, +1px | barras de título de janela |
| Número grande | `{typography.numeric-lg}` | 44 VT323 | contador, porcentagem em destaque |
| Número médio | `{typography.numeric-md}` | 24 VT323 | "24/40", progresso em linha |

### Principles

- VT323 nunca em frase: no máximo 3 palavras ou um número. Abaixo de 18px ela fica ilegível.
- Números que mudam (contador, timer, porcentagem, "x/y") usam VT323 ou Plex Mono, que têm largura fixa e não "pulam".
- Texto longo (guias, ajuda) tem largura máxima de cerca de 72 caracteres.
- Loading termina com "…" ("Carregando…"); aspas tipográficas (“ ”); botões em frase normal ("Salvar marcação", não "Salvar Marcação").

### Note on Font Substitutes

Se as fontes embarcadas não carregarem: Chakra Petch → Bahnschrift (Windows) / Avenir Next Condensed (macOS); IBM Plex Sans → Segoe UI / SF Pro; VT323 → Consolas / Menlo; IBM Plex Mono → Consolas / Menlo.

## Layout

### Spacing System

Base 4: `{spacing.xxs}` 4, `{spacing.xs}` 8, `{spacing.sm}` 12, `{spacing.md}` 16, `{spacing.lg}` 24, `{spacing.xl}` 32, `{spacing.xxl}` 48. Dentro de painel o padrão é `{spacing.md}`. Entre painéis, `{spacing.lg}`. Entre título de página e conteúdo, `{spacing.lg}`.

### Grid & Container

- Janela mínima 980 × 620. Barra lateral fixa de 232px em `{colors.sunken}`.
- Área de conteúdo com margens de 28px nas laterais e 24px em cima e embaixo.
- Cards de módulo/plugin em grade que reflui de 1 a 3 colunas conforme a largura. O card tem largura mínima de 284px (`ModuleCard.MIN_WIDTH`): o título elide com dica e a descrição quebra linha inteira, nunca é cortada.
- Guia de platina em janela própria: mínimo 720 × 560.

### Whitespace Philosophy

Ferramenta de live é densidade média: tudo à mão, sem rolagem desnecessária. Espaço vazio separa grupos; ele não é decoração. Sem hero gigante em página de ferramenta: o topo da página é título + ação principal.

### Wallpaper

A área de conteúdo é pintada por `WallpaperSurface` com um pixmap em cache: degradê vertical, sol listrado no horizonte, grid em perspectiva e scanlines. Os painéis ficam por cima, opacos, então o texto nunca encosta na arte. As opções ficam em `tokens.WALLPAPERS` e o usuário escolhe em Configurações › "Papel de parede" (chave `hub.wallpaper`):

| Chave | Rótulo | Clima |
|---|---|---|
| `futurefunk` (padrão) | Future funk | roxo → magenta, sol e grid fortes |
| `noite` | Noite roxa | mesmo desenho, mais escuro e discreto |
| `liso` | Liso | `{colors.canvas}` plano, para quem quer zero distração |

Papel de parede novo entra como mais uma chave em `WALLPAPERS`, sempre com um painel opaco por cima garantindo o contraste do texto.

## Elevation & Depth

| Nível | Como | Onde |
|---|---|---|
| 0 | papel de parede (ou `{colors.canvas}` liso) | fundo da área de conteúdo |
| 1 | `{colors.surface}` + borda `{colors.hairline}` + sombra dura 4/4 | `panel-window`, `module-card` |
| 2 | nível 1 + borda `{colors.primary}` + faixa `{colors.brand}` + brilho suave | `panel-window-featured` (máx. 1 por tela) |
| sobreposto | diálogo modal com o fundo escurecido a 60% | `QDialog`, `QMessageBox` |

A sombra dura é pintada no `paintEvent` (um retângulo deslocado, sem desfoque). Isso é barato e fica nítido. `QGraphicsDropShadowEffect` só se for indispensável.

### Decorative Depth

- `synth-hero`: sol em gradiente `{colors.synth-sun-top}` → `{colors.synth-sun-bottom}` cortado por 5 faixas horizontais, horizonte em `{colors.synth}` e grid de perspectiva em `{colors.primary}` a 35%. Pintado em QPainter (vetor), sem imagem.
- Brilho (glow) só em três lugares: painel em destaque, preenchimento de progresso e indicador ao vivo.

## Shapes

### Border Radius Scale

`{rounded.none}` 0, `{rounded.xs}` 2, `{rounded.sm}` 4, `{rounded.md}` 6, `{rounded.full}` pílula.

Regra única: **tudo é quase reto** (`{rounded.sm}`). As exceções escritas são: chips de status e o ponto de estado são pílula (`{rounded.full}`); callouts usam `{rounded.xs}`; ícones de app (os quadrados de 48px dos cards) usam `{rounded.md}`. O chanfro de 10px no canto superior direito é exclusivo do `panel-window`: é a assinatura herdada da identidade atual.

## Iconography

Dois conjuntos com funções diferentes. A interface precisa de clareza; os momentos de marca precisam de personalidade.

### Ícones de interface (`icon-ui`)

Linha "HUD" na grade 24: traço reto de 2px, pontas quadradas, junções em quina e o chanfro do `panel-window` nos retângulos. Uma cor só, pelo estado: `{colors.ink-muted}` em repouso, `{colors.ink}` no hover, `{colors.primary}` ativo, `{colors.danger}` destrutivo e `{colors.ink-faint}` desabilitado. A espessura não escala com o desenho: são 2px reais em 20 e 24px, e 1,5px em 16px.

Conjunto: `home` (o robô sidekick), `plugins`, `platinas`, `hotkey`, `diagnostics`, `settings`, `help`, `about`, `marker`, `counter`, `folder`, `backup` (disquete), `alert`, `favorite`, `live`, `update`, `popout`, `remove` e `back`.

Ícone sem texto tem nome acessível (`setAccessibleName`) e tooltip. Ícone com texto fica à esquerda do rótulo.

### Ícones de marca (`icon-brand`)

Pixel-art na grade 12×12, com células sólidas e sem antisserrilhado. Usa três tintas: a cor do papel do ícone (por exemplo `{colors.success}` no troféu, `{colors.brand}` no ao vivo), um acento e `{colors.ink}` para brilho.

Só aparecem em 48px (cards das ferramentas nativas, telas vazias, conquistas) ou 96px (onboarding). Com 4px por célula em 48px, a arte continua inteira nas escalas 125%, 150% e 200% do Windows. Abaixo de 48px as células ficam desiguais.

Conjunto: `sidekick`, `trophy`, `floppy`, `gamepad`, `crt`, `cassette`, `star`, `live`, `puzzle` (plugin sem ícone próprio), `marker` e `counter`.

## Motion

- Hover e pressionado: 120ms, ease-out. Botão pressionado desce 1px.
- Troca de página: fade de 120ms. Sem deslizar.
- Progresso anima quando o valor muda (300ms). Nada fica em loop, exceto o pulso do indicador "ao vivo".
- Configuração "Reduzir animações" desliga tudo que não seja feedback imediato.

## Components

### Buttons

Um `button-primary` por área visível: é a ação que o usuário veio fazer ("Marcar agora", "Instalar", "Salvar"). O resto é `button-secondary`. Ações de navegação leve ("Voltar aos guias", "Ver todas") são `button-ghost`. Remover/apagar é `button-danger` e sempre pede confirmação, com "Não" como padrão. Todo botão tem os estados hover, pressionado, foco e desabilitado.

### Cards & Containers

- `panel-window` agrupa uma seção. A barra de título traz o nome em caixa alta à esquerda e um metadado curto à direita ("3/4", "v1.0.2", "AO VIVO").
- `module-card` representa um módulo ou plugin: ícone de 48px, título em uma linha com reticências, descrição em no máximo 2 linhas com reticências, `status-chip` e ações. Nunca corta texto sem reticências.

### Inputs & Forms

`input` em `{colors.sunken}` com borda `{colors.control-border}`. Rótulo acima do campo, erro abaixo em `{colors.danger}` com a correção sugerida. O placeholder mostra um exemplo e termina com "…" ("Ex.: boss derrotado…"). Placeholder nunca substitui o rótulo.

### Navigation

Barra lateral em `{colors.sunken}`. Item ativo: fundo `{colors.surface-raised}`, texto `{colors.ink}` e barra de 3px em `{colors.brand}` à esquerda, sem caixa contornada. Ícones de 24px (`icon-ui`), em `{colors.primary}` no item ativo. Subitens (ferramentas dentro de Plugins) com recuo de 18px e ícone de 20px, ainda com traço de 2px.

### Badges & Status

`status-chip` = ponto colorido + rótulo curto em pílula. Ele **não pode parecer campo de texto**: não tem borda interna e tem o ponto. Estados: ok (`{colors.success}`), atenção (`{colors.warning}`), erro (`{colors.danger}`), neutro (`{colors.ink-faint}`), ao vivo (`{colors.brand}`, com pulso).

Selos em `{typography.hud-label}`:
- `live-badge` ("AO VIVO", "GRAVANDO"): fundo `{colors.brand}`.
- `trophy-badge` ("PLATINADO", "OBTIDO"): fundo `{colors.success}`.
- `tag-missable` (`PERDÍVEL`): contorno `{colors.warning}`, sempre visível.
- `tag-spoiler` (`SPOILER`): contorno neutro; o conteúdo protegido só aparece ao clicar, como manda o `GUIA_DE_PLATINA.md`.

### Signature Components

- **`segmented-progress`**: progresso em blocos, como barra de vida. É usado nas platinas (troféus, passos do guia) e em downloads. O rótulo "24/40" vem em `{typography.numeric-md}` ao lado.
- **`numeric-display`**: o número do Contador, porcentagens e timers em VT323 grande.
- **`synth-hero`**: faixa de 140px no topo do Início, no onboarding e nas telas vazias. Fica ao lado do título da página, não acima dele.

## Do's and Don'ts

### Do
- Um `button-primary` por área; o resto é secundário.
- Um `panel-window-featured` por tela, no máximo.
- Use `{colors.success}` para todo progresso e conquista, e só para isso.
- Mostre números que mudam em `{typography.numeric-md}` ou `{typography.numeric-lg}`.
- Elida texto com "…" (`ElidedLabel`, `QFontMetrics.elidedText`) em vez de cortar, sempre com o texto inteiro na dica (tooltip). Descrições quebram linha em vez de elidir.
- Dê a toda lista vazia uma mensagem e a próxima ação ("Nenhum favorito ainda. Gerenciar favoritos").
- Leia cores, fontes e espaços de `tokens.py`, nunca de um hex escrito no widget.

### Don't
- Não coloque borda neon em degradê em todo painel: brilho é exceção.
- Não use emoji na interface (🔔 ✓ ❤ ✉ 🎉); use o `icon-ui` correspondente.
- Não use degradê em ícone, nem misture os dois conjuntos num mesmo grupo (barra lateral é sempre `icon-ui`).
- Não use `icon-brand` abaixo de 48px.
- Não repita o logo na área de conteúdo: ele já está na barra lateral.
- Não use VT323 em frases nem abaixo de 18px.
- Não use `{colors.brand}` em botões nem `{colors.synth}` em controles.
- Não faça chip de status com cara de campo de texto.
- Não ponha texto direto sobre o papel de parede ou o `synth-hero`: sempre dentro de um painel.

## Responsive Behavior

Desktop, não web:

- Janela mínima 980 × 620. Abaixo de 1100px de largura, a grade de cards passa para 2 colunas; abaixo de 800px de área útil, para 1.
- Páginas longas rolam dentro da área de conteúdo; a barra lateral também rola se não couber (comportamento atual).
- Alvo clicável mínimo de 32px de altura (botões têm 34px).
- Guia de platina embutido usa a largura disponível; quando ficar apertado, o usuário usa "Abrir em janela".

## Plugins e guias

Plugins e guias montam a própria página com `build_page()`. Para combinarem com o hub:

- Usem os tokens expostos pelo hub (`streamer_sidekick.ui.tokens`, previsto), com fallback para os valores deste arquivo quando rodarem fora dele.
- Usem os `objectName` do tema (`PrimaryButton`, painel-janela, `status-chip`…) em vez de estilos próprios.
- Não definam fundo de página nem fonte global: o hub já define.
- Guias de platina usam `segmented-progress` para troféus e passos, `tag-missable`/`tag-spoiler` para as tags da spec e `callout-info`/`callout-warning`/`callout-danger` para avisos (um nível de caixa só, nunca caixa dentro de caixa).

Quando a API de tokens existir, `PLUGIN_STANDARD.md` e `GUIA_DE_PLATINA.md` passam a apontar para esta seção.

## Iteration Guide

1. Mude **um componente por vez** e tire um print de antes e depois (script de render com APPDATA isolado).
2. Sempre referencie tokens (`{colors.primary}`, `button-primary-hover`), nunca o valor solto.
3. Variante nova = nova entrada em `components:` (`-hover`, `-pressed`, `-disabled`, `-active`).
4. Cor nova só entra com papel escrito na tabela de Colors. Se não tiver papel, não entra.
5. Rode a skill `web-design-guidelines` (mapeamento Qt) nas telas alteradas antes do PR.

## Known Gaps

Estado em 2026-10-01 (branch `sidekick-os`, ainda não publicada):

- Feito: `ui/tokens.py` (fonte única), QSS e `QPalette` gerados dos tokens, fontes embarcadas em `assets/fonts`, `panel-window` (`NeonPanel`), `status-chip`, `segmented-progress`, `synth-hero`, ícones `icon-ui`/`icon-brand`, Início e Plugins reorganizados, nenhum hex nem emoji escrito à mão na UI.
- Feito: papel de parede future funk com seletor, neutros roxos, estados de foco/pressionado/desabilitado em todos os botões, `ElidedLabel` com dica, confirmação em toda ação destrutiva, estados vazios nas listas. Verificador de texto cortado: 0 problemas em 980×620, 1280×800 e 1600×900.
- `numeric-display` ainda não substituiu o número do Contador e dos overlays.
- Os guias de platina e os plugins de terceiros pintam a própria página: herdam tema e fontes, mas só adotam painel-janela, progresso em blocos e tags quando forem atualizados.
- A configuração "Reduzir animações" não existe.
- Sem tema claro (decisão: o app é só escuro).
- Tempos de animação são a proposta inicial; ajustar no uso real.

## Migração a partir da 0.8.x

| Hoje | Token |
|---|---|
| `#0A0B12` (fundo geral, `VOID_BLACK`) | `{colors.canvas}` |
| `#080A10`, `#080B12` | `{colors.sunken}` |
| `#0B111A`, `#0D121B`, `#0D1621`, `#0E1621`, `#101722`, `#111722`, `#11161C` | `{colors.surface}` |
| `#101B28`, `#111B28`, `#141826`, `#142632`, `#151E2C` | `{colors.surface-raised}` |
| `#273140` (`PANEL_BORDER`) | `{colors.hairline}` |
| `#303946` | `{colors.hairline-strong}` |
| `#596373` (borda de campo) | `{colors.control-border}` |
| `#F3F6FF` (`SOFT_WHITE`), `#FFFFFF`, `#D9E4EF`, `#C7D0DD` | `{colors.ink}` |
| `#A8B0BC` (`MUTED`) | `{colors.ink-muted}` |
| `#687180` | `{colors.ink-faint}` |
| `#37F2FF` | `{colors.primary}` |
| `#14383F`, `#10242A`, `#174A52` | `{colors.primary-tint}` |
| `#FF4FD8` | `{colors.brand}` |
| `#B9FF43`, `#93E6C6` | `{colors.success}` |
| `#FFD37A` | `{colors.warning}` |
| `#FF7A7A` | `{colors.danger}` |
| Bahnschrift / Segoe UI / Consolas | Chakra Petch / IBM Plex Sans / IBM Plex Mono |
| raios 5, 6, 7, 8, 10px | `{rounded.sm}` (exceções na seção Shapes) |
| `NeonIcon` (degradê ciano→rosa) | `icon-ui` |
| `marker_icon.png`, `counter_icon.png` | `icon-brand` `marker` e `counter` |
