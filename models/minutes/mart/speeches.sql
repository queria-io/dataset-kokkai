{# 発言 1 件 1 行。まだ無い発言だけを追記する。会議録は登録後に書き換えない前提で、前回の行は残す #}
{{ config(materialized='incremental', incremental_strategy='append') }}

select
    speech_id,
    meeting_id,
    date,
    house,
    meeting_name,
    speech_order,
    speaker,
    speaker_yomi,
    speaker_group,
    speaker_position,
    speaker_role,
    speech,
    start_page,
    speech_url,
    fetched_at
from {{ ref('stg_speeches') }}
{% if is_incremental() %}
where speech_id not in (select speech_id from {{ this }})
{% endif %}
order by date, meeting_id, speech_order
