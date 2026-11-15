{# 会議 1 件 1 行。まだ無い会議だけを追記する #}
{{ config(materialized='incremental', incremental_strategy='append') }}

select distinct on (meeting_id)
    meeting_id,
    house,
    session,
    meeting_name,
    issue,
    date,
    image_kind,
    closing,
    meeting_url,
    pdf_url,
    fetched_at
from {{ ref('stg_speeches') }}
{% if is_incremental() %}
where meeting_id not in (select meeting_id from {{ this }})
{% endif %}
order by meeting_id, fetched_at desc
