-- Streamer Sidekick: banco do modo nuvem.
--
-- Cole este arquivo inteiro no SQL Editor do Supabase e rode uma vez.
-- Pode rodar de novo com seguranca: tudo aqui e "create or replace" ou
-- protegido por "if not exists".
--
-- O que este arquivo cria:
--   profiles  : uma linha por usuario (criada sozinha no primeiro login)
--   files     : os arquivos sincronizados, um por linha, conteudo em base64
--   is_admin(), is_active() : usadas nas politicas de seguranca
--   admin_list_profiles(), admin_set_profile() : o que o painel admin chama
--   gatilhos : updated_at automatico, cota por usuario, perfil no signup
--
-- A seguranca e o RLS (row level security): cada usuario so enxerga e mexe
-- nas proprias linhas, e so enquanto o perfil estiver ativo. A "anon key"
-- que vai no app e publica por desenho; e o RLS que protege os dados.

-- ============================================================ profiles ==

create table if not exists public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  email        text,
  display_name text,
  is_admin     boolean not null default false,
  active       boolean not null default true,
  ads_enabled  boolean not null default true,
  created_at   timestamptz not null default now(),
  last_seen_at timestamptz
);

alter table public.profiles enable row level security;

-- Funcoes "security definer": rodam com os privilegios do dono, nao do
-- usuario. E o que evita a recursao infinita de uma politica em profiles
-- que consulta profiles.
create or replace function public.is_admin()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select coalesce((select is_admin from public.profiles where id = auth.uid()), false);
$$;

create or replace function public.is_active()
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select coalesce((select active from public.profiles where id = auth.uid()), false);
$$;

-- Cria o perfil quando o usuario faz o primeiro login pelo Google.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name)
  values (
    new.id,
    new.email,
    coalesce(
      new.raw_user_meta_data ->> 'full_name',
      new.raw_user_meta_data ->> 'name',
      split_part(coalesce(new.email, ''), '@', 1)
    )
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- Politicas: cada um le o proprio perfil; o admin le todos.
drop policy if exists "profiles: ler o proprio ou admin" on public.profiles;
create policy "profiles: ler o proprio ou admin"
  on public.profiles for select
  using (id = auth.uid() or public.is_admin());

drop policy if exists "profiles: atualizar o proprio" on public.profiles;
create policy "profiles: atualizar o proprio"
  on public.profiles for update
  using (id = auth.uid())
  with check (id = auth.uid());

-- Privilegio por coluna: o proprio usuario so pode mudar nome e last_seen.
-- is_admin, active e ads_enabled so mudam pelas funcoes de admin abaixo.
revoke update on public.profiles from authenticated;
grant select on public.profiles to authenticated;
grant update (display_name, last_seen_at) on public.profiles to authenticated;

-- =============================================================== files ==

create table if not exists public.files (
  id          bigserial primary key,
  user_id     uuid not null references auth.users (id) on delete cascade,
  path        text not null,
  content_b64 text,
  sha256      text not null,
  size        integer not null check (size >= 0 and size <= 2 * 1024 * 1024),
  deleted     boolean not null default false,
  updated_at  timestamptz not null default now(),
  unique (user_id, path)
);

-- Windows e macOS nao distinguem Zelda.txt de zelda.txt; o banco tambem nao pode.
create unique index if not exists files_user_lower_path
  on public.files (user_id, lower(path));

create index if not exists files_user_updated
  on public.files (user_id, updated_at desc);

alter table public.files enable row level security;

drop policy if exists "files: so as proprias, so quando ativo" on public.files;
create policy "files: so as proprias, so quando ativo"
  on public.files for all
  using (user_id = auth.uid() and public.is_active())
  with check (user_id = auth.uid() and public.is_active());

grant select, insert, update, delete on public.files to authenticated;
grant usage, select on sequence public.files_id_seq to authenticated;

-- updated_at e do servidor, nunca do cliente: relogio de PC nao decide nada.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists files_set_updated_at on public.files;
create trigger files_set_updated_at
  before insert or update on public.files
  for each row execute procedure public.set_updated_at();

-- Cota: 20 MB por usuario. O banco gratuito tem 500 MB para todo mundo;
-- um bug ou um cliente mal-intencionado nao pode enche-lo.
create or replace function public.enforce_quota()
returns trigger
language plpgsql
as $$
declare
  total bigint;
begin
  if new.deleted then
    return new;
  end if;
  select coalesce(sum(size), 0) into total
    from public.files
   where user_id = new.user_id
     and not deleted
     and id <> coalesce(new.id, -1);
  if total + new.size > 20 * 1024 * 1024 then
    raise exception 'quota exceeded: %', total + new.size
      using errcode = 'P0001';
  end if;
  return new;
end;
$$;

drop trigger if exists files_enforce_quota on public.files;
create trigger files_enforce_quota
  before insert or update on public.files
  for each row execute procedure public.enforce_quota();

-- ================================================================ admin ==

-- O painel admin do app chama estas duas. So funcionam para quem tem
-- is_admin = true; para os outros devolvem erro de permissao.

create or replace function public.admin_list_profiles()
returns setof public.profiles
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.is_admin() then
    raise exception 'not admin' using errcode = '42501';
  end if;
  return query select * from public.profiles order by created_at desc;
end;
$$;

create or replace function public.admin_set_profile(
  target        uuid,
  p_active      boolean default null,
  p_ads_enabled boolean default null
)
returns public.profiles
language plpgsql
security definer
set search_path = public
as $$
declare
  r public.profiles;
begin
  if not public.is_admin() then
    raise exception 'not admin' using errcode = '42501';
  end if;
  update public.profiles
     set active      = coalesce(p_active, active),
         ads_enabled = coalesce(p_ads_enabled, ads_enabled)
   where id = target
   returning * into r;
  return r;
end;
$$;

grant execute on function public.admin_list_profiles() to authenticated;
grant execute on function public.admin_set_profile(uuid, boolean, boolean) to authenticated;
grant execute on function public.is_admin() to authenticated;
grant execute on function public.is_active() to authenticated;

-- ============================================================== pronto ==
-- Depois do SEU primeiro login pelo app, rode UMA vez (troque o e-mail):
--
--   update public.profiles set is_admin = true where email = 'ricardothezouro@gmail.com';
