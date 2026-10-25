# O config sobe por chave, e os atalhos sobem por sistema

O `config.json` do app mistura **preferências** com **configuração da máquina**, então ele nunca sobe inteiro. A nuvem guarda só uma lista fechada de chaves (favoritos, papel de parede, iniciar minimizado, fechar para a bandeja, arquivo ativo do Marcador, mensagens rápidas e atalhos). Pastas, iniciar com o sistema, onboarding e última versão nunca sobem. Ao baixar, as preferências são aplicadas pelo `ConfigStore` do app aberto, e não trocando o arquivo no disco: o `ConfigStore` guarda o config em memória e regravaria o arquivo inteiro no próximo `set()`, desfazendo a troca.

Os atalhos (do hub e das mensagens rápidas) sobem **separados por sistema**: o que foi gravado no macOS nunca substitui o do Windows, e vice-versa. Uma combinação com Cmd não existe no Windows, e uma livre num sistema pode estar reservada no outro. Um segundo PC do mesmo sistema herda os atalhos do primeiro.

## Consequences

- Chave nova no config só sobe se entrar na lista. O padrão é não subir.
- Os atalhos de cada contador ficam dentro do preset e viajam com ele; esse caso é tratado na interface (fase 2), não aqui.
