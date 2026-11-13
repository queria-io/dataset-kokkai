# 国会会議録

[国会会議録検索システム](https://kokkai.ndl.go.jp/)に収録されている衆議院・参議院の本会議と委員会の会議録を、会議と発言のテーブルにしたデータセットです。毎週、[検索用 API](https://kokkai.ndl.go.jp/api.html) から新しく登録された会議録を取得します。

| テーブル | 内容 |
| --- | --- |
| `minutes.meetings` | 1 行が 1 会議録（本会議・委員会などの 1 号）。院名・国会回次・会議名・号数・開会日・会議録の URL |
| `minutes.speeches` | 1 行が 1 発言。開会日・会議名・発言者・会派・肩書きと発言の本文 |

- `meeting_id`（会議録 ID）で 2 つのテーブルを結合できます
- `speech_order` が 0 の行は、出席者・議事日程などを載せた会議録の冒頭です
- 会議録は開会から数週間〜数か月たって登録されます。毎回、前回の最後の開会日の 180 日前から再取得し、まだ無い会議と発言を追記します（過去分の取得中は最後の開会日から続けます）

## 使い方

語を含む発言を新しい順に:

```sql
SELECT date, meeting_name, speaker, speaker_group, speech_url
FROM kokkai.minutes.speeches
WHERE speech LIKE '%待機児童%'
ORDER BY date DESC
LIMIT 20;
```

会派ごとの発言数:

```sql
SELECT speaker_group, count(*) AS speeches
FROM kokkai.minutes.speeches
WHERE date >= DATE '2025-01-01' AND speaker_group IS NOT NULL
GROUP BY speaker_group
ORDER BY speeches DESC;
```

## ビルド

```bash
uv sync
scripts/build.sh
```

取得の間隔は 1 秒です。1 回のビルドで取得するのは前回の続きから 1,100 日分（`KOKKAI_MAX_DAYS`）までで、100 分（`KOKKAI_MAX_MINUTES`）を超えたら取得済みの月までで止めます。1947 年からすべてを取得するときは手元で `KOKKAI_MAX_DAYS=40000 KOKKAI_MAX_MINUTES=2000 scripts/build.sh` を実行します。

## 出典と利用条件

出典：国会会議録検索システム（国立国会図書館）（https://kokkai.ndl.go.jp/）の検索用 API を利用して取得・加工したものです。

[利用条件](https://kokkai.ndl.go.jp/api.html)は国立国会図書館ウェブサイトのコンテンツ利用規約に従います。データベース自体と国立国会図書館職員の発言の著作権は国立国会図書館に、その他の発言の著作権は各発言者にあります。著作権法の権利制限規定（政治上の演説又は陳述の利用、引用、電子計算機による情報解析など）に当たる場合は許諾なしで利用できます。許諾の要否は利用者が確認してください。
