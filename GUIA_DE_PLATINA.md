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
| Painel de canto cortado | `NeonPanel` |
| Título da página | `PageTitle` |
| Título de seção | `SectionTitle` |
| Texto secundário | `Muted` |
| Selo de status | `StatusPill` |
| Área rolável | `PageScroll` |

Convenções da aba Platinas:

- **Cores de tier** — bronze `#CD7F32`, prata `#C0C0C0`, ouro `#FFD700`,
  platina `#E5E4E2`.
- **Progresso sempre visível**, no topo: barra + contagem.
- **Busca**, quando o guia for grande o bastante para justificar.
- **Nada de estilo inline concorrendo com o tema.** O `QApplication` já aplica a
  paleta neon; se você redefinir fundo e fonte na mão, o guia destoa.

Os guias existentes (`Assistente-de-platina-Dredge`, `Guia-de-Platina-Wolong`,
`House-fliper-assistente-de-platina`) servem de referência **visual**. Não copie a
estrutura deles — o jogo é outro.

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
> - **Desenhe a estrutura que ESTE jogo pede.** Não clone o formato de outro
>   guia: escolha as abas e o modelo de dados a partir do que a platina deste
>   jogo realmente exige — rota, coletáveis, chefes, receitas, o que for.
> - Conteúdo: **\<cole o material do jogo — troféus com id/nome/tier/dica, e o
>   que mais o guia precisar\>**.
> - Gere também `requirements.txt`, `.gitignore`, `README.md` e a entrada do
>   `platinas.json`.
