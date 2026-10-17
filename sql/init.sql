-- Runs once, when the Postgres volume is created.
create schema if not exists raw;
create schema if not exists audit;
create schema if not exists marts;

create table if not exists audit.pipeline_runs (
    run_id      serial primary key,
    started_at  timestamptz not null default now(),
    finished_at timestamptz,
    status      text not null default 'running',
    message     text
);

-- Values found in a source that no mapping knows about (the run stops when there are any).
create table if not exists audit.unmapped_values (
    run_id       int references audit.pipeline_runs,
    tenant_id    text,
    field        text,
    source_value text,
    row_count    int,
    detected_at  timestamptz not null default now()
);

-- Totals computed straight from each source, used to reconcile the warehouse.
create table if not exists audit.source_totals (
    run_id       int references audit.pipeline_runs,
    tenant_id    text,
    source_table text,
    row_count    int,
    amount_total numeric(20, 2)
);

-- Read-only role for analysts: marts only, and one tenant at a time (row-level security).
do $$ begin
    if not exists (select from pg_roles where rolname = 'analyst') then
        create role analyst login password 'analyst';
    end if;
end $$;
grant connect on database partnerhub to analyst;
grant usage on schema marts to analyst;
