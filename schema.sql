-- Smart Office Memory Phase 1: run this file in Supabase SQL Editor.
-- Uses ordinary authenticated Supabase accounts and row-level security (RLS).
-- Important: do not expose service_role / secret API keys in the app.

begin;

create table if not exists public.projects (
  id bigint generated always as identity primary key,
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null check (char_length(name) between 1 and 150),
  description text not null default '',
  assignee text not null default '',
  status text not null default 'กำลังดำเนินการ',
  created_at timestamptz not null default now(),
  unique (id, owner_id)
);

create table if not exists public.documents (
  id bigint generated always as identity primary key,
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  project_id bigint,
  title text not null check (char_length(title) between 1 and 150),
  original_name text not null,
  file_type text not null check (file_type in ('.pdf', '.docx', '.txt')),
  storage_path text not null unique,
  content text not null default '',
  summary text not null default '',
  created_at timestamptz not null default now(),
  constraint documents_project_owner_fk foreign key (project_id, owner_id)
    references public.projects(id, owner_id)
);

create table if not exists public.tasks (
  id bigint generated always as identity primary key,
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  project_id bigint not null,
  title text not null check (char_length(title) between 1 and 150),
  assignee text not null default '',
  status text not null default 'รอดำเนินการ',
  due_date date,
  created_at timestamptz not null default now(),
  foreign key (project_id, owner_id) references public.projects(id, owner_id) on delete cascade
);

create table if not exists public.activity_logs (
  id bigint generated always as identity primary key,
  owner_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  action text not null,
  details text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_projects_owner on public.projects(owner_id);
create index if not exists idx_documents_owner on public.documents(owner_id);
create index if not exists idx_tasks_owner on public.tasks(owner_id);
create index if not exists idx_logs_owner on public.activity_logs(owner_id);

-- Upgrade projects and documents created using the original schema.
alter table public.projects add column if not exists assignee text not null default '';
alter table public.documents drop constraint if exists documents_project_id_owner_id_fkey;
alter table public.documents drop constraint if exists documents_project_owner_fk;
alter table public.documents add constraint documents_project_owner_fk
  foreign key (project_id, owner_id) references public.projects(id, owner_id);

-- Preserve legacy records while validating new writes.
alter table public.projects drop constraint if exists projects_input_check;
alter table public.projects add constraint projects_input_check check (
  btrim(name) <> '' and char_length(description) <= 2000 and char_length(assignee) <= 100
  and status in ('รอเริ่ม', 'กำลังดำเนินการ', 'เสร็จแล้ว', 'ยกเลิก')
) not valid;
alter table public.tasks drop constraint if exists tasks_input_check;
alter table public.tasks add constraint tasks_input_check check (
  btrim(title) <> '' and char_length(assignee) <= 100
  and status in ('รอดำเนินการ', 'กำลังดำเนินการ', 'เสร็จแล้ว', 'ยกเลิก')
) not valid;
alter table public.documents drop constraint if exists documents_input_check;
alter table public.documents add constraint documents_input_check check (
  btrim(title) <> '' and char_length(original_name) between 1 and 200
  and char_length(content) <= 100000
  and storage_path ~ ('^' || owner_id::text || '/[a-f0-9]{32}\.' || substring(file_type from 2) || '$')
) not valid;

create index if not exists idx_documents_project_owner on public.documents(project_id, owner_id);
create index if not exists idx_tasks_project_owner on public.tasks(project_id, owner_id);
create index if not exists idx_logs_owner_latest on public.activity_logs(owner_id, id desc);

revoke all on public.projects, public.documents, public.tasks, public.activity_logs from anon, public, authenticated;
grant select, insert, update, delete on public.projects, public.tasks to authenticated;
grant select, insert, delete on public.documents to authenticated;
grant update (title, project_id) on public.documents to authenticated;
grant select on public.activity_logs to authenticated;
grant usage on sequence public.projects_id_seq, public.documents_id_seq, public.tasks_id_seq to authenticated;

alter table public.projects enable row level security;
alter table public.documents enable row level security;
alter table public.tasks enable row level security;
alter table public.activity_logs enable row level security;

-- Safe to rerun after a partial setup.
drop policy if exists "owner_projects" on public.projects;
create policy "owner_projects" on public.projects
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

drop policy if exists "owner_documents" on public.documents;
create policy "owner_documents" on public.documents
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

drop policy if exists "owner_tasks" on public.tasks;
create policy "owner_tasks" on public.tasks
  for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

drop policy if exists "owner_logs_read" on public.activity_logs;
create policy "owner_logs_read" on public.activity_logs
  for select to authenticated
  using ((select auth.uid()) = owner_id);

drop policy if exists "owner_logs_add" on public.activity_logs;

-- Log the committed operation in the same transaction as the row change.
create or replace function public.log_office_change()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  previous jsonb;
  current_row jsonb;
  item jsonb;
  changes jsonb;
  action_name text;
begin
  previous := case when tg_op <> 'INSERT' then to_jsonb(old) end;
  current_row := case when tg_op <> 'DELETE' then to_jsonb(new) end;
  item := coalesce(current_row, previous);
  if (select auth.uid()) is distinct from (item->>'owner_id')::uuid then
    return null;
  end if;

  action_name := case tg_op when 'INSERT' then 'เพิ่ม' when 'UPDATE' then 'แก้ไข' else 'ลบ' end
    || case tg_table_name when 'projects' then 'โครงการ' when 'tasks' then 'งาน' else 'เอกสาร' end;
  if tg_op = 'UPDATE' then
    select coalesce(jsonb_agg(key order by key), '[]'::jsonb)
      into changes
      from jsonb_each(current_row)
      where previous->key is distinct from value;
    if changes = '[]'::jsonb then
      return null;
    end if;
  end if;
  insert into public.activity_logs (owner_id, action, details)
  values ((item->>'owner_id')::uuid, action_name,
          '#' || (item->>'id') || coalesce(' ' || changes::text, ''));
  return null;
end;
$$;
revoke all on function public.log_office_change() from public, anon, authenticated;

drop trigger if exists log_office_change on public.projects;
create trigger log_office_change after insert or update or delete on public.projects
  for each row execute function public.log_office_change();
drop trigger if exists log_office_change on public.tasks;
create trigger log_office_change after insert or update or delete on public.tasks
  for each row execute function public.log_office_change();
drop trigger if exists log_office_change on public.documents;
create trigger log_office_change after insert or update or delete on public.documents
  for each row execute function public.log_office_change();

-- Private bucket: 3 MB per file; text, PDF, DOCX only.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'office-docs', 'office-docs', false, 3145728,
  array['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
)
on conflict (id) do update
  set public = false,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- Each user's files live at {auth.uid()}/{random_uuid}.ext.
-- RLS for bucket is enforced by the first path segment (the user ID).
drop policy if exists "office_files_read" on storage.objects;
create policy "office_files_read" on storage.objects
  for select to authenticated
  using (
    bucket_id = 'office-docs'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

drop policy if exists "office_files_add" on storage.objects;
create policy "office_files_add" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'office-docs'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

drop policy if exists "office_files_delete" on storage.objects;
create policy "office_files_delete" on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'office-docs'
    and (storage.foldername(name))[1] = (select auth.uid())::text
  );

commit;
