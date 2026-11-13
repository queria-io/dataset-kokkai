{# 会議 1 件 1 行。まだ無い会議だけを追記する #}
{{ config(materialized='incremental', incremental_strategy='append') }}

select distinct on (issueID)
    issueID as meeting_id,
    nameOfHouse as house,
    session,
    nameOfMeeting as meeting_name,
    issue,
    date,
    imageKind as image_kind,
    closing,
    meetingURL as meeting_url,
    pdfURL as pdf_url,
    fetched_at
from {{ ref('raw_speeches') }}
{% if is_incremental() %}
where issueID not in (select meeting_id from {{ this }})
{% endif %}
order by issueID, fetched_at desc
