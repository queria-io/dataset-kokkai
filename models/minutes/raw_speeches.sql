{# 取得した発言 (data/kokkai/speeches/*.ndjson.gz) を型を付けて読む。同じ発言が
   重なった月の取り直しで 2 回入ったときは、後に取った方を残す #}
{{ config(materialized='ephemeral') }}

select *
from read_json(
    'data/kokkai/speeches/*.ndjson.gz',
    format = 'newline_delimited',
    columns = {
        speechID: 'VARCHAR', issueID: 'VARCHAR', imageKind: 'VARCHAR', searchObject: 'INTEGER',
        session: 'INTEGER', nameOfHouse: 'VARCHAR', nameOfMeeting: 'VARCHAR', issue: 'VARCHAR',
        date: 'DATE', closing: 'VARCHAR', speechOrder: 'INTEGER', speaker: 'VARCHAR',
        speakerYomi: 'VARCHAR', speakerGroup: 'VARCHAR', speakerPosition: 'VARCHAR',
        speakerRole: 'VARCHAR', speech: 'VARCHAR', startPage: 'INTEGER', speechURL: 'VARCHAR',
        meetingURL: 'VARCHAR', pdfURL: 'VARCHAR', fetched_at: 'TIMESTAMPTZ'
    }
)
qualify row_number() over (partition by speechID order by fetched_at desc) = 1
