# Os plugins ficam fora da nuvem na 0.10

A 0.10 sincroniza só os dados do hub: **preferências**, Marcador, Contador e **progresso** das platinas. As preferências dos plugins (o roadmap previa levá-las) ficam para uma versão seguinte.

Cada plugin oficial guarda seus dados de um jeito: o StreamOn grava fora da pasta do app (`%APPDATA%\StreamLigar`) e guarda caminhos de programas desta máquina; o Subtitler guarda a chave da Groq no mesmo arquivo das preferências. Sincronizar esses arquivos como estão vazaria segredo ou levaria caminhos inúteis para outro PC.

Quando os plugins entrarem, será por **declaração**: cada plugin diz no `PLUGIN_STANDARD.md` quais arquivos sobem e quais chaves são segredo. O hub nunca adivinha o que é seguro subir de um plugin.
