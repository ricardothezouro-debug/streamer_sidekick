# O progresso das platinas é fundido, não sobrescrito

Para os `.json`, a regra geral de **conflito** é "a nuvem vence" (a cópia local vai para o **backup da nuvem**). O **progresso** dos guias de platina é a exceção: ele é fundido em três vias contra a **base**. O que foi marcado num lado desde a base entra; o que foi desmarcado num lado sai; o resto fica como estava.

"A nuvem vence" apagaria troféus marcados no outro PC; uma união simples traria de volta um passo que a pessoa desmarcou. Só a comparação com a base separa "desmarquei aqui" de "marquei lá".

Funciona com os dois formatos que os guias usam hoje: a lista de ids marcados (DREDGE, House Flipper, Wo Long, Kingdom Hearts, Alan Wake, Code: Veronica) e o objeto com essa lista em `done` (The Witcher 3), em que os outros campos seguem a regra geral dos `.json`. Guias novos devem guardar o progresso como lista de ids marcados (`GUIA_DE_PLATINA.md`).

## Consequences

- Um guia que guardar o progresso em outro formato cai na regra geral dos `.json` e pode perder marcações em conflito.
- Só o `progress.json` sobe. A posição na tela (`ui.json`) e o cache de imagens ficam no PC.
