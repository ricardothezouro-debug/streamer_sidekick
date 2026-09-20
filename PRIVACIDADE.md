# Política de Privacidade do Streamer Sidekick

Última atualização: 20 de setembro de 2026.

O Streamer Sidekick é um aplicativo gratuito para computador, feito para quem
faz live. Esta página explica o que ele guarda, onde e por quê. Está escrita
para ser lida, não para cumprir tabela.

## Os dois modos

Ao abrir pela primeira vez, você escolhe entre **modo local** e **modo nuvem**.
Dá para trocar depois, nas Configurações.

### Modo local

Nada seu sai do seu computador. O app guarda tudo em uma pasta de dados do
seu usuário no sistema (marcadores, configurações, presets do contador,
progresso das platinas).

As únicas conexões que o app faz nesse modo são com o GitHub, para verificar
se há atualização do app e para baixar plugins do catálogo. Essas conexões
não enviam nada sobre você.

Alguns plugins usam serviços de terceiros com uma conta sua: o Subtitler usa
a Groq com a sua chave; o ClipIt usa a Twitch com a sua autorização. Nesses
casos o que vai para o serviço é o que você mandou (um áudio para transcrever,
um pedido de clipe), e a chave ou o token ficam só no seu computador.

### Modo nuvem

Ao entrar com a sua conta Google, o app passa a guardar uma cópia dos seus
dados num servidor, para você abrir o app em outro computador e encontrar
tudo igual.

**O que é guardado:**

- O e-mail e o nome da sua conta Google. É o que identifica a sua conta no
  app. Não temos a sua senha do Google; o login acontece no site do Google.
- Os arquivos que você sincroniza: marcadores, configurações do app,
  presets do contador e seus ícones, progresso das platinas e preferências dos
  plugins.
- A data do último acesso.

**O que nunca é guardado na nuvem:**

- Chaves de API e tokens de plugins (Groq, Twitch ou qualquer outro).
- Senhas.
- Vídeos, áudios ou clipes.
- Caminhos de pastas do seu computador.

**Onde fica:** nos servidores do Supabase, nos Estados Unidos (região
us-east-1). A transmissão é sempre por HTTPS.

**Quem tem acesso:**

- Você. Cada conta só enxerga os próprios dados; isso é garantido no
  banco de dados, não só no aplicativo.
- O mantenedor do Streamer Sidekick, como dono da infraestrutura, tem acesso
  técnico ao banco. Pelo painel administrativo do app ele vê e-mail, nome, data
  de criação e último acesso, e pode ativar ou desativar contas. O conteúdo dos
  seus arquivos só é acessado para dar suporte, e só se você pedir.
- Ninguém mais. Não vendemos, não compartilhamos e não usamos seus dados para
  nada além de fazer o app funcionar.

**Anúncios:** o modo nuvem pode exibir anúncios para ajudar a pagar o servidor.
Se um provedor de anúncios for adotado, esta página vai dizer qual é e o que
ele coleta, antes de ele entrar no app.

## Seus dados são seus

- **Baixar tudo:** nas Configurações há um botão que salva todos os seus dados
  da nuvem numa pasta, em arquivos simples (`.txt`, `.json`, `.png`).
- **Sair da nuvem:** desconectar a conta apaga a sessão do seu computador. Os
  dados locais continuam com você. Os dados na nuvem ficam guardados até você
  pedir a exclusão.
- **Apagar a conta:** mande um e-mail para streamersidekick@gmail.com do mesmo
  endereço da conta. Tudo é apagado, incluindo os arquivos.

## Idade

O app não é feito para menores de 13 anos, e o modo nuvem não deve ser usado
por menores sem um responsável.

## Mudanças nesta política

Quando algo mudar, esta página é atualizada aqui no repositório, com a data no
topo. O histórico de versões fica no próprio GitHub.

## Contato

streamersidekick@gmail.com
