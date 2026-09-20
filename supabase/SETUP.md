# Modo nuvem: como configurar o Supabase

Este guia é para quem mantém o Streamer Sidekick. O usuário final não precisa
fazer nada disso: ele só clica em "Entrar com Google".

Tempo estimado: 20 minutos. Tudo no plano gratuito.

## 1. Criar o projeto no Supabase

1. Entre em https://supabase.com e crie uma organização, se ainda não tiver.
2. **New project**. Região: **South America (São Paulo)**. Guarde a senha do
   banco num lugar seguro (você não vai usar no app, mas o painel pede).
3. Quando o projeto subir, vá em **Project Settings → API** e copie:
   - **Project URL** (algo como `https://abcdefgh.supabase.co`)
   - **anon public** key (começa com `eyJ`)

A anon key é pública por desenho: ela vai dentro do app. O que protege os
dados é o RLS, que o passo 4 liga.

## 2. Criar o cliente OAuth no Google

1. https://console.cloud.google.com → crie um projeto (ou use um seu).
2. **APIs & Services → OAuth consent screen**:
   - Tipo **External**
   - Nome do app: `Streamer Sidekick`; e-mail de suporte: o seu
   - Escopos: só `openid`, `email`, `profile`
   - **Publish app**. Sem isso o app fica em "Testing", que só aceita até 100
     e-mails listados à mão. Com esses três escopos não há verificação do
     Google a fazer.
3. **Credentials → Create credentials → OAuth client ID**:
   - Tipo **Web application** (sim, mesmo sendo um app de desktop: quem
     conversa com o Google é o Supabase)
   - **Authorized redirect URIs**: exatamente
     `https://SEU-PROJETO.supabase.co/auth/v1/callback`
     (troque pelo Project URL do passo 1)
4. Copie o **Client ID** e o **Client Secret**.

## 3. Ligar o Google no Supabase

1. **Authentication → Providers → Google**: ligue, cole Client ID e Secret.
2. **Authentication → URL Configuration**:
   - **Site URL**: pode ser o Project URL mesmo.
   - **Redirect URLs**: adicione estas três, exatamente assim:
     ```
     http://127.0.0.1:53682/callback
     http://127.0.0.1:53683/callback
     http://127.0.0.1:53684/callback
     ```
     São as portas em `scripts/cloud_probe.py` e, depois, em
     `core/cloud/constants.py`. Se mudar lá, mude aqui.
     Use `127.0.0.1`, não `localhost`.
3. **Authentication → Sign In / Providers → Email**: desligue. Só Google.
4. **Authentication → Sessions**: deixe a rotação de refresh token ligada
   (padrão). Expiração do access token: 3600 s (padrão).

## 4. Criar o banco

1. **SQL Editor → New query**.
2. Cole o conteúdo inteiro de `supabase/schema.sql` e rode.
3. Confira em **Table Editor**: existem `profiles` e `files`, as duas com o
   cadeado de RLS ligado.
4. Confira em **Database → Functions**: `is_admin`, `is_active`,
   `handle_new_user`, `set_updated_at`, `enforce_quota`, `admin_list_profiles`,
   `admin_set_profile`.

## 5. Rodar a prova

No seu computador, com o repositório do Sidekick:

1. Crie o arquivo `<dados do app>/cloud/endpoint.json`:
   - macOS: `~/Library/Application Support/StreamerSidekick/cloud/endpoint.json`
   - Windows: `%APPDATA%\StreamerSidekick\cloud\endpoint.json`
   ```json
   {"url": "https://SEU-PROJETO.supabase.co", "anon_key": "eyJ..."}
   ```
2. Rode:
   ```
   PYTHONPATH=src python scripts/cloud_probe.py
   ```
   (no Windows: `set PYTHONPATH=src` antes, ou use o venv do projeto)
3. O navegador abre no Google. Entre com a sua conta. A aba diz "pode fechar".
4. O terminal mostra um `[ok]` por passo. O resultado esperado é **TUDO OK**.

Rode no Windows e no macOS. A prova não grava nada.

### Erros comuns

| O que aparece | Onde olhar |
|---|---|
| `callback do login FALHOU` com "redirect" na mensagem | Passo 3.2: as três URLs precisam estar exatamente iguais |
| Navegador abre, mas cai em "Testing"/"app não verificado" | Passo 2.2: **Publish app** |
| `perfil criado pelo gatilho FALHOU` | Passo 4: o SQL não rodou inteiro; rode de novo |
| `troca do code por sessao FALHOU` com `invalid_grant` | O code vale 5 minutos e só uma vez; rode a prova de novo |
| Página HTML em vez de JSON, ou HTTP 5xx | O projeto está pausado; **Restore** no painel |
| `permission denied for table` | Passo 4: os `grant` do final do SQL não rodaram |

## 6. Você virar admin

Depois do primeiro login pela prova (ou pelo app), no **SQL Editor**:

```sql
update public.profiles set is_admin = true where email = 'ricardothezouro@gmail.com';
```

Rode a prova de novo: o último passo deve listar os perfis.

## 7. Colocar no app e no keep-alive

1. No repositório do Sidekick: `core/cloud/constants.py` recebe o Project URL
   e a anon key (a fase seguinte cria esse arquivo).
2. **GitHub → Settings → Secrets and variables → Actions**: crie
   `SUPABASE_URL` e `SUPABASE_ANON_KEY`. O workflow `keepalive.yml` faz uma
   consulta mínima segunda e quinta, para o projeto não pausar.

## 8. Operação do dia a dia

- **Ver usuários**: Authentication → Users.
- **Desativar uma conta** (ela cai para o modo local, dados preservados):
  `update public.profiles set active = false where email = '...';`
  Ou pelo painel admin do app, quando existir.
- **Banir de verdade** (nem loga mais): Authentication → Users → o usuário →
  **Ban user**.
- **Acompanhar uso**: Reports. O que importa no plano gratuito é o tamanho do
  banco (500 MB) e o tráfego de saída (5 GB/mês).
- **Backup**: o plano gratuito não faz. Uma vez por mês, SQL Editor:
  `select * from public.files;` → **Download CSV**.
- **Se o projeto pausar**: Dashboard → **Restore**. Leva uns minutos.

## 9. Checklist antes de publicar a 0.9

Nos dois sistemas:

1. App zerado → escolhe Nuvem → navegador → Google → "conectado como você".
2. Marca um evento em A → linha em `files` → B recebe ao abrir.
3. Os dois marcam no mesmo `.txt` sem internet → reconectam → os dois têm
   todas as linhas.
4. Mesmo preset editado nos dois → o remoto vence; a cópia local está em
   `cloud/backup/`.
5. Preset apagado em A → B move o dele para o backup.
6. Troca a pasta do Marcador em A → nada é apagado na nuvem.
7. `active = false` → rodapé "conta desativada", app segue local; `true` volta.
8. Projeto pausado → app abre normal, "nuvem indisponível".
9. "Baixar tudo para uma pasta" → arquivos simples.
10. Desliga a nuvem → apaga um marcador → liga → o marcador volta.
11. Fecha no meio de uma sincronização → reabre e termina.
