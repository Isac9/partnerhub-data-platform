{# Use the schema names as written (staging, marts...) instead of public_staging. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}

{# Every mart table: analysts only see the tenant set in their session (SET app.tenant_id = 'acme'). #}
{% macro enable_tenant_rls() %}
    alter table {{ this }} enable row level security;
    drop policy if exists tenant_isolation on {{ this }};
    create policy tenant_isolation on {{ this }} for select to analyst
        using (tenant_id = current_setting('app.tenant_id', true));
    grant select on {{ this }} to analyst;
{% endmacro %}
