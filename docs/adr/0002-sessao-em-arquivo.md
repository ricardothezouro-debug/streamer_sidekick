# A sessão fica num arquivo protegido, não no cofre do sistema

A **sessão** do modo nuvem é guardada em `cloud/session.json`, na pasta de dados do app, gravada de forma atômica e com permissão só para o usuário do sistema. Guardamos só o refresh token: ele é trocado a cada uso (a rotação está ligada no Supabase) e pode ser revogado pelo painel.

Não usamos o cofre do sistema (Gerenciador de Credenciais no Windows, Keychain no macOS) porque isso traria uma dependência nova a empacotar com o PyInstaller nos dois sistemas, para proteger um token que já expira e gira sozinho. É o mesmo padrão que o ClipIt usa para os tokens da Twitch.

## Considered Options

- Cofre do sistema via a biblioteca `keyring`: mais protegido contra outro programa lendo o arquivo, mas com custo de empacotamento e de suporte nos dois sistemas.
