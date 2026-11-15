{# 発言 1 件 1 行。列名を付け替える。同じ発言が重なった月の取り直しで 2 回入ったときは、後に取った方を残す #}

select
    speechID as speech_id,
    issueID as meeting_id,
    nameOfHouse as house,
    session,
    nameOfMeeting as meeting_name,
    issue,
    date,
    imageKind as image_kind,
    closing,
    speechOrder as speech_order,
    speaker,
    speakerYomi as speaker_yomi,
    speakerGroup as speaker_group,
    speakerPosition as speaker_position,
    speakerRole as speaker_role,
    speech,
    startPage as start_page,
    speechURL as speech_url,
    meetingURL as meeting_url,
    pdfURL as pdf_url,
    fetched_at
from {{ ref('raw_speeches') }}
qualify row_number() over (partition by speechID order by fetched_at desc) = 1
