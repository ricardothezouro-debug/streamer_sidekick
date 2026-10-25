# Streamer Sidekick

Hub desktop de ferramentas para a live (Marcador, Contador, plugins e guias de platina), que funciona sozinho no PC e, se a pessoa quiser, guarda os dados na nuvem.

## Nuvem

**Modo local**:
O jeito padrão de usar o app: tudo fica só no PC, sem conta.
_Avoid_: offline, modo desconectado

**Modo nuvem**:
O jeito opcional de usar o app em que a pessoa entra com o Google e os dados dela acompanham ela entre os PCs.
_Avoid_: modo online, conta premium

**Sincronização**:
O momento em que o app compara os dados do PC com os da nuvem e leva cada mudança para o lado que não a tem. Acontece ao abrir, ao fechar e no botão, nunca sozinha no meio do uso.
_Avoid_: sync automático, backup

**Base**:
A versão de um arquivo que estava igual no PC e na nuvem ao fim da última sincronização; é ela que diz quem mudou desde então.
_Avoid_: snapshot, cópia anterior

**Conflito**:
Quando o PC e a nuvem mudaram o mesmo arquivo desde a base.
_Avoid_: divergência, colisão

**Preferências**:
As escolhas da pessoa que fazem sentido em qualquer PC (favoritos, papel de parede, arquivo ativo do Marcador, mensagens rápidas, atalhos) e que, por isso, sobem para a nuvem.
_Avoid_: config, configurações (o arquivo de configuração mistura preferências com configuração da máquina)

**Configuração da máquina**:
O que só vale para um PC (pastas escolhidas, iniciar com o sistema, o que já foi visto na primeira abertura) e nunca sobe.
_Avoid_: config local, ajustes do sistema

**Progresso**:
O conjunto de itens marcados num guia de platina.
_Avoid_: checklist, save, estado do guia

**Exclusão**:
O registro, na nuvem, de que a pessoa apagou um arquivo num PC; nos outros PCs o arquivo vai para o backup da nuvem em vez de sumir.
_Avoid_: deleção, remoção

**Backup da nuvem**:
A pasta deste PC onde vai a versão local de um arquivo sempre que a sincronização a substitui ou a exclui.
_Avoid_: lixeira, histórico, versão anterior

**Sessão**:
O login de uma pessoa neste PC, que dura até ela sair ou a conta ser desativada.
_Avoid_: token (é só a peça técnica da sessão), login salvo

## Comunicação dentro do app

**Evento**:
Um aviso que uma parte do app (ou um plugin) publica quando algo acontece, como uma marcação salva, para quem quiser reagir.
_Avoid_: sinal, notificação, mensagem
