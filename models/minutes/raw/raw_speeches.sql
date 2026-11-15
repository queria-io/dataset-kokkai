{# 取得した発言 (data/kokkai/speeches/*.ndjson.gz)。API の speechRecord の項目をそのまま読む #}

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
