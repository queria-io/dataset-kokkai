{# 発言 1 件 1 行。まだ無い発言だけを追記する。会議録は登録後に書き換えない前提で、前回の行は残す #}
{{ config(materialized='incremental', incremental_strategy='append') }}

select
    speechID as speech_id,
    issueID as meeting_id,
    date,
    nameOfHouse as house,
    nameOfMeeting as meeting_name,
    speechOrder as speech_order,
    speaker,
    speakerYomi as speaker_yomi,
    speakerGroup as speaker_group,
    speakerPosition as speaker_position,
    speakerRole as speaker_role,
    speech,
    startPage as start_page,
    speechURL as speech_url,
    fetched_at
from {{ ref('raw_speeches') }}
{% if is_incremental() %}
where speechID not in (select speech_id from {{ this }})
{% endif %}
order by date, meeting_id, speech_order
