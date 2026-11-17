-- Already deployed via the Supabase connection. This copy documents the persistent schema.
create table if not exists public.projects (id uuid primary key default gen_random_uuid(),owner_id uuid not null references auth.users(id),name text not null,created_at timestamptz default now());
create table if not exists public.datasets (id uuid primary key default gen_random_uuid(),owner_id uuid not null references auth.users(id),project_id uuid not null references public.projects(id),filename text not null,storage_path text,row_count integer,column_count integer,created_at timestamptz default now());
create table if not exists public.analysis_runs (id uuid primary key default gen_random_uuid(),owner_id uuid not null references auth.users(id),dataset_id uuid not null references public.datasets(id),status text not null default 'pending',result jsonb,error_message text,created_at timestamptz default now(),completed_at timestamptz);
alter table public.projects enable row level security;
alter table public.datasets enable row level security;
alter table public.analysis_runs enable row level security;
-- RLS owner policies and private storage bucket are installed on the connected Supabase project.
