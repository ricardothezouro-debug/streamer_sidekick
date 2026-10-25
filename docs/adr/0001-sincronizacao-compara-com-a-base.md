# A sincronização compara arquivos com a base, não ouve eventos

A sincronização acontece só ao abrir, ao fechar e no botão. Nesses momentos ela compara cada arquivo do PC com a **base** (o hash da versão que estava igual dos dois lados na última sincronização) e com o que está na nuvem: mudou só no PC, sobe; só na nuvem, baixa; nos dois, é **conflito** (união de linhas nos `.txt` do Marcador; a nuvem vence nos `.json`, com a cópia local guardada em backup).

Ela não depende do barramento de **eventos**, de propósito: há quem escreva nos arquivos por fora do hub (o ClipIt anexa linhas no `.txt` do Marcador direto no disco), e o app pode ter sido fechado à força; um sincronizador movido a eventos perderia essas mudanças. O barramento existe para os plugins reagirem a coisas (como o "F2 marca e clipa"), não para a nuvem.

## Consequences

- A base fica só nesta máquina. Sem ela (primeira sincronização num PC, ou base apagada), todo arquivo que existe dos dois lados e difere é tratado como conflito.
- Não ligar a sincronização a eventos "para ficar mais em tempo real": isso contraria a decisão de não fazer polling e de sincronizar só nos três momentos.
