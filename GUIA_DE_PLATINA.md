# Como criar um Guia de Platina (para o Streamer Sidekick)

Um **guia de platina** é um plugin (categoria `platina`) que aparece na aba
**Platinas** do Streamer Sidekick: o roteiro de um jogo específico, com progresso
salvo, dicas e imagens.

> **Uso com IA:** entregue **este arquivo + o `PLUGIN_STANDARD.md`** para uma IA,
> junto do material do jogo. Ela gera o repositório completo.

Este documento é uma **especificação, não um template**. Ele diz o que o guia
precisa cumprir e com que cara ele tem que ficar — não como escrever cada linha.

---

## ⚠️ Regra que não se negocia: Windows **e** macOS

Todo guia roda nos dois sistemas. O Streamer Sidekick é publicado para Windows e
para macOS, e um guia que só funciona num deles não entra no catálogo.

As armadilhas são poucas e todas silenciosas — nenhuma dá erro no Windows, então
passam despercebidas até alguém abrir no Mac:

| Nunca | O que acontece no Mac | Use |
|---|---|---|
| `os.getenv("APPDATA")` | Progresso vai parar numa pasta oculta na home | o helper de pasta (abaixo) |
| `urllib.request.urlopen(...)` direto | `CERTIFICATE_VERIFY_FAILED` — **nenhuma imagem carrega**, em silêncio | o helper de download (abaixo) |
| `os.startfile(...)` | `AttributeError` | `platform_utils.open_path()` |
| `C:\...`, `%APPDATA%`, `.exe` em texto visível | Mente para quem está no Mac | monte o caminho e mostre o real |

Antes de publicar, abra o guia nos dois sistemas: ele tem que exibir imagens e o
progresso tem que sobreviver a fechar e reabrir.

---

## O que é fixo e o que é livre

**Livre — e deve variar por jogo.** Um guia de Wo Long tem batalhas, bandeiras e
coletáveis. Um de House Flipper tem casas e compradores. Um de DREDGE tem peixes,
santuários e docas. Modele os dados e as abas como **aquele** jogo pede: crie as
seções que fizerem sentido, o número de abas que fizer sentido, a ordem que fizer
sentido. Dois guias não precisam ter a mesma forma — nem devem.

**Fixo — e não se discute.** Três coisas:

1. **O contrato de plugin** (`module_info()` + `build_page()`), descrito no
   `PLUGIN_STANDARD.md`.
2. **A estética**, para o guia parecer parte do hub e não um app estranho dentro
   dele.
3. **A canalização de plataforma**: onde grava e como baixa.

O resto é seu.

---

## 1. Contrato

Vale o `PLUGIN_STANDARD.md` inteiro. Específico da categoria `platina`:

- `module_info()` deve devolver `status` com o progresso legível — algo como
  `"12/51 troféus"`. É o que aparece no card antes de abrir o guia.
- `accent` é a cor do jogo (hex). Escolha uma que converse com a identidade dele.
- `build_page()` devolve a página inteira do guia.
- `help_text()` (opcional, recomendado) explica como usar **este** guia.

O `module_info()` precisa funcionar com e sem o Sidekick importável — use a
`ModuleInfo` dele quando der, e uma cópia local compatível quando não.

## 2. Estética

É o que faz todos os guias parecerem da mesma família. Use os `objectName`s que o
tema do hub já estiliza (lista completa no `PLUGIN_STANDARD.md`, seção 6):

| Elemento | `objectName` |
|---|---|
| Painel-janela (chanfro e sombra dura) | `NeonPanel` |
| Título da página | `PageTitle` |
| Título de seção | `SectionTitle` |
| Texto secundário | `Muted` |
| Número (troféus, "24/40") | `Numeric` |
| Selo de status | `StatusPill` |
| Área rolável | `PageScroll` |

Desde a v0.9 o design system é o **Sidekick OS** ([`DESIGN.md`](DESIGN.md)): cores
lidas de `streamer_sidekick.ui.tokens`, progresso em blocos (`SegmentedProgress`),
tags `PERDÍVEL` em `warning` e `SPOILER` neutra, callouts de um nível só (nunca
caixa dentro de caixa) e nada de emoji.

Convenções da aba Platinas:

- **Cores de tier** — bronze `#CD7F32`, prata `#C0C0C0`, ouro `#FFD700`,
  platina `#E5E4E2`.
- **Progresso sempre visível**, no topo: barra + contagem.
- **Topo em três níveis.** Entre o topo e o conteúdo vai uma linha fina
  (`hairline`, sem degradê: no Sidekick OS o brilho é exceção) com bolinhas em
  `primary` no meio — em repouso são pontos; ao passar o mouse crescem e
  mostram a seta do que fazem. Nível 1: tudo à vista (uma bolinha ▲). Nível 2:
  só título, progresso e abas — é o nível em que o guia SEMPRE abre (duas
  bolinhas, ▼ e ▲). Nível 3: some tudo e o progresso vira um balão flutuante,
  arrastável, com os contadores e a própria bolinha ▼ (o clique duplo também
  volta). Toda troca de nível é animada — e NÃO animando a altura no layout,
  que num guia grande custa ~125 ms por quadro: o componente congela a tela,
  aplica o estado final de uma vez e anima a passagem entre dois retratos da
  página num overlay. A posição do balão é lembrada num `ui.json` na pasta do
  guia, separado do `progress.json`; o nível não. O rodapé (nome, "não oficial",
  pasta do progresso) fica atrás de um "?" no canto inferior direito. Os quatro
  guias trazem o componente pronto em `topbar.py` — copie-o.
- **Busca**, quando o guia for grande o bastante para justificar.
- **Nada de estilo inline concorrendo com o tema.** O `QApplication` já aplica a
  paleta do Sidekick OS; se você redefinir fundo e fonte na mão, o guia destoa.

Os guias existentes (`Assistente-de-platina-Dredge`, `Guia-de-Platina-Wolong`,
`House-fliper-assistente-de-platina`, `Guia-De-Platina-KingdomHearts1`) servem de
referência **visual** — os quatro já têm o topo em três níveis. Não copie a
estrutura deles — o jogo é outro.

### Guias não lineares e jogos de mundo aberto

Não transforme todo jogo numa sequência de passos. Quando a ordem for livre, o
guia deve funcionar como uma rede de segurança e não como um corredor.

- Organize o conteúdo pelos eixos que realmente ajudam naquele jogo. Regiões,
  capítulos, sistemas paralelos e tipos de atividade podem coexistir.
- Deixe o usuário marcar o próprio avanço. A tela inicial deve usar esse estado
  para mostrar o que está disponível, o que ainda está pendente e o que precisa
  ser resolvido antes de continuar.
- Crie **portões de segurança** antes de missões, capítulos ou ações que mudem o
  mundo. Cada portão deve reunir numa lista curta todos os perdíveis ainda
  abertos, mesmo quando eles pertencem a regiões diferentes.
- Preserve a liberdade de exploração. Uma ordem recomendada pode existir, mas
  só deve ser obrigatória quando houver uma dependência real.
- Prefira blocos compactos com resumo e progresso agregado. Detalhes, escolhas,
  listas grandes e explicações ficam recolhidos até o usuário pedir para vê-los.

### Tags, spoilers e conteúdo perdível

Tags são informação funcional, não apenas decoração. Elas precisam ter texto,
contraste e significado consistentes em todas as telas.

- `PERDÍVEL` fica sempre visível. Nunca esconda a existência de um risco atrás
  de um spoiler.
- `SPOILER` esconde somente a informação sensível. O conteúdo aparece ao clicar
  na tag ou no controle associado.
- Um item pode combinar tags, por exemplo `PERDÍVEL` e `SPOILER`.
- Ofereça uma ação global para revelar ou esconder todos os spoilers da página,
  sem mudar o padrão inicial de conteúdo recolhido.
- Se uma escolha não ameaça a platina, as opções e recompensas podem aparecer
  dentro do spoiler.
- Se uma escolha pode bloquear a platina, mostre diretamente a ação segura. Não
  apresente uma opção perigosa como se tivesse o mesmo peso. A explicação da
  consequência pode continuar protegida por spoiler.
- Quando fizer sentido, classifique atividades como `NECESSÁRIA`, `ÚTIL`,
  `OPCIONAL` ou `PODE IGNORAR`. A interface principal deve destacar o necessário
  e agrupar o restante para não virar uma lista poluída.

### Estilo editorial

O texto do guia deve parecer escrito e revisado por alguém que conhece o jogo.

- Escreva em português do Brasil, com frases diretas e vocabulário natural.
- Use o nome oficial em português e, quando ajudar na busca, acrescente o nome
  em inglês entre parênteses.
- Não use travessões como muleta de ritmo. Prefira ponto, vírgula, dois-pontos ou
  parênteses.
- Corte introduções genéricas, repetições e adjetivos promocionais. Diga o que o
  jogador precisa fazer, quando fazer e por que aquilo importa.
- Faça uma revisão humana de clareza e consistência antes de publicar.

## 3. Canalização de plataforma

A única parte que não varia, e a que quebra se você improvisar.

**Onde gravar.** Progresso fica **fora** da pasta do plugin, senão some a cada
atualização. Peça o caminho ao Sidekick, que já conhece a convenção de cada
sistema:

```python
from streamer_sidekick.core.paths import user_data_dir

pasta = user_data_dir("platinas") / GUIDE_ID   # criada se não existir
```

**Como baixar imagem.**

```python
from streamer_sidekick.core import net

with net.urlopen(requisicao, timeout=20) as resposta:
    dados = resposta.read()
```

**Cache de imagens.** Conteúdo visual remoto deve ser salvo na pasta de dados do
guia depois do primeiro download. Nas próximas aberturas, use a cópia local e
atualize-a somente quando necessário. Se a rede falhar, mantenha a imagem já
armazenada e mostre um estado compreensível quando ainda não houver cache.

Ambos exigem `"min_sidekick_version": "0.7.1"` no catálogo.

Se o guia também roda standalone (fora do Sidekick), envolva os dois imports num
`try/except ImportError` e caia num equivalente que respeite os três sistemas:
`%APPDATA%` no Windows, `~/Library/Application Support` no macOS, `$XDG_CONFIG_HOME`
(ou `~/.config`) no Linux. Nunca só o primeiro.

**Cuidado com falha silenciosa.** Download de imagem costuma rodar em `QThread`
com `except Exception` largo. Se engolir o erro sem sinalizar, o sintoma no Mac
não é uma mensagem: é o guia aparecer sem imagem nenhuma, sem explicação. Registre
o erro em algum lugar.

## 4. Dados do jogo

Concentre o conteúdo num módulo só (`guide_data.py` é a convenção), separado da
interface. Isso mantém o guia fácil de revisar e de atualizar quando sair DLC.

O mínimo que todo guia tem:

```python
GUIDE_ID = "elden-ring"        # kebab-case, único, vira a pasta de progresso
GAME_NAME = "Elden Ring"
GAME_SUBTITLE = "..."
ACCENT = "#B9FF43"
```

Mais a lista de troféus. Cada um precisa de um **`id` estável** — é a chave do
progresso salvo; se você renumerar entre versões, o usuário perde o que marcou.
Junto disso vêm nome, tier, dica e, quando ajudar, uma URL de imagem (prefira CDN
estável para hotlink, como a da Steam).

Itens acompanháveis além dos troféus também precisam de IDs estáveis. Para um
guia com exploração livre, o modelo deve conseguir representar, quando
aplicável:

- região, capítulo ou sistema a que o item pertence;
- momento em que fica disponível e prazo máximo;
- pré-requisitos e dependências;
- ação que conclui, bloqueia ou falha o item;
- relevância para a platina;
- tags funcionais, inclusive `PERDÍVEL` e `SPOILER`;
- escolhas, recompensas e texto protegido por spoiler;
- troféus, colecionáveis ou outros objetivos relacionados;
- imagem e texto alternativo;
- estado marcado manualmente pelo usuário.

Modele também os portões de segurança como dados. Não espalhe prazos críticos
somente em textos da interface. Isso permite calcular pendências, montar o painel
da fase atual e testar se um avanço perigoso está sendo avisado.

**A partir daí, modele o que o jogo exigir**: rotas, coletáveis por região,
receitas, ordem de chefes, o que for. Essas estruturas são o valor do guia.

## 5. Estrutura do repositório

Sugestão, não regra:

```
platina-<jogo>/
  src/
    platina_<jogo>/        <- nome ÚNICO por guia (dois iguais colidem)
      __init__.py
      module.py            adaptador de plugin
      page.py              a interface (do tamanho que o jogo pedir)
      guide_data.py        o conteúdo
      ...                  o que mais o guia precisar
  requirements.txt
  README.md
  .gitignore
```

Use **imports relativos** dentro do pacote: assim o nome da pasta pode mudar sem
quebrar nada.

## 6. Publicar

1. Repositório público no GitHub.
2. Teste standalone **nos dois sistemas**:
   - Windows: `set PYTHONPATH=src && python -m platina_<jogo>`
   - macOS/Linux: `PYTHONPATH=src python -m platina_<jogo>`

   Confirme nos dois: abre, imagens carregam, e marcar algo sobrevive a fechar e
   reabrir.
3. Adicione a entrada no `platinas.json` do Streamer Sidekick:

```json
{
  "id": "elden-ring",
  "name": "Elden Ring",
  "description": "Guia de platina do Elden Ring.",
  "repo": "seu-usuario/platina-elden-ring",
  "ref": "main",
  "version": "1.0.0",
  "src_subdir": "src",
  "module": "platina_elden_ring.module",
  "accent": "#B9FF43",
  "min_sidekick_version": "0.7.1"
}
```

O guia aparece na aba **Platinas** para instalar. Ao subir uma versão, bump o
`version` (SemVer) e escreva um `changelog` dizendo o que mudou para o jogador.

---

## Prompt pronto para a IA

> Você recebeu `PLUGIN_STANDARD.md` e `GUIA_DE_PLATINA.md`. Crie um guia de
> platina para o jogo **\<JOGO\>**.
>
> - Pacote `platina_<slug_do_jogo>`, com imports relativos.
> - **Rode no Windows e no macOS.** Nada de `os.getenv("APPDATA")`, `urlopen`
>   direto, `os.startfile` ou `C:\` / `%APPDATA%` / `.exe` em texto visível.
>   Progresso e download vão pelos helpers do Sidekick.
> - Siga a estética da aba Platinas (`NeonPanel`, `PageTitle`, `SectionTitle`,
>   `Muted`, `StatusPill`, `PageScroll`, cores de tier), sem estilo inline
>   concorrendo com o tema.
> - Para jogos não lineares, preserve a exploração livre e use estado marcado
>   pelo usuário, portões de segurança e alertas de perdíveis.
> - Use tags combináveis. `PERDÍVEL` fica sempre visível; `SPOILER` revela o
>   conteúdo sob demanda, com uma ação global por página.
> - Classifique o conteúdo por relevância e mantenha a interface principal
>   focada no que é necessário para a platina.
> - Escreva em português do Brasil natural e revisado. Não use travessões como
>   recurso de estilo nem encha o texto com introduções genéricas.
> - **Desenhe a estrutura que ESTE jogo pede.** Não clone o formato de outro
>   guia: escolha as abas e o modelo de dados a partir do que a platina deste
>   jogo realmente exige — rota, coletáveis, chefes, receitas, o que for.
> - Conteúdo: **\<cole o material do jogo — troféus com id/nome/tier/dica, e o
>   que mais o guia precisar\>**.
> - Gere também `requirements.txt`, `.gitignore`, `README.md` e a entrada do
>   `platinas.json`.
