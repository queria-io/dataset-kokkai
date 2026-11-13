"""国会会議録検索システムの検索用 API から、発言を 1 件ずつ取得する。

発言単位出力（/api/speech）を、開会日（from・until）で 1 か月ずつに絞って取得する。1 回で
返るのは 100 件までなので、nextRecordPosition をたどってページを送る。

会議録は開会から数週間〜数か月たって登録される。毎回、公開中の表の最後の開会日から
REFETCH_DAYS 日前までさかのぼって再取得する（過去分の取得中は最後の開会日から続ける）。初回と過去分は MAX_DAYS 日ずつ進め、
MAX_MINUTES 分を超えたら取得済みの月までで止める（1 年の発言数は年代で 10 万〜21 万件と
差があり、日数だけでは Sync の制限時間に収まらない）。

出力: data/kokkai/speeches/<年>-<月>.ndjson.gz（1 行 = 1 発言、API の speechRecord のまま）

データソース: 国会会議録検索システム 検索用 API（国立国会図書館）
https://kokkai.ndl.go.jp/api.html
"""

import gzip
import json
import logging
import os
import time
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from shared.fetch import fetch, replacing

logger = logging.getLogger("pipelines")

API = "https://kokkai.ndl.go.jp/api/speech"
USER_AGENT = "dataset-kokkai (+https://github.com/queria-io/dataset-kokkai)"
OUTPUT = Path("data/kokkai/speeches")
# 第 1 回国会の開会日
FIRST_DAY = date(1947, 5, 20)
REFETCH_DAYS = 180
MAX_DAYS = int(os.environ.get("KOKKAI_MAX_DAYS", "1100"))
# Sync の timeout_minutes (150) から dbt build と fdl commit・push の時間を引いた残り
MAX_MINUTES = int(os.environ.get("KOKKAI_MAX_MINUTES", "100"))
PAGE_SIZE = 100
# 利用条件は短時間の大量アクセスを控えるよう求めている。1 回ずつ間を空ける
INTERVAL_SECONDS = 1.0


def page(start: date, end: date, record: int) -> dict:
    query = urlencode(
        {"from": start.isoformat(), "until": end.isoformat(), "startRecord": record,
         "maximumRecords": PAGE_SIZE, "recordPacking": "json"}
    )
    try:
        body = json.loads(fetch(f"{API}?{query}", user_agent=USER_AGENT))
    except HTTPError as error:
        # 条件の誤りは 400 と JSON の message で返る
        raise SystemExit(f"API が {error.code} を返した: {start}〜{end} {record}: {error.read()[:300].decode('utf-8', 'replace')}") from None
    if "message" in body:
        raise SystemExit(f"API がエラーを返した: {start}〜{end} {record}: {body['message']}")
    return body


def speeches(start: date, end: date) -> Iterator[dict]:
    record = 1
    while record:
        body = page(start, end, record)
        yield from body.get("speechRecord", [])
        record = body.get("nextRecordPosition")
        time.sleep(INTERVAL_SECONDS)


def months(start: date, end: date) -> list[tuple[date, date]]:
    """start から end までを暦月ごとに区切る。端の月は start・end で切る。"""
    firsts = [date(y, m, 1) for y in range(start.year, end.year + 1) for m in range(1, 13)]
    spans = [(max(f, start), min(next_month(f) - timedelta(days=1), end)) for f in firsts]
    return [(s, e) for s, e in spans if s <= e]


def next_month(day: date) -> date:
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def published_cursor() -> date | None:
    """公開中の minutes.meetings の最後の開会日。FDL_WORKING が無いか、表がまだ無ければ None。

    speeches と同じ値で、行数が少ない meetings を読む。
    """
    working = os.environ.get("FDL_WORKING")
    if not working:
        return None
    import duckdb

    con = duckdb.connect(config={"custom_user_agent": os.environ.get("QUERIA_USER_AGENT", "")})
    con.execute("INSTALL ducklake; LOAD ducklake; INSTALL httpfs; LOAD httpfs;")
    con.execute(f"ATTACH 'ducklake:{working.replace(chr(39), chr(39) * 2)}' AS previous (READ_ONLY, META_TYPE 'sqlite')")
    try:
        return con.sql("select max(date) from previous.minutes.meetings").fetchall()[0][0]
    except duckdb.CatalogException as error:
        logger.info("  公開中の表が無い: %s", error)
        return None
    finally:
        con.close()


def span_to_fetch(cursor: date | None, today: date, has_catalog: bool) -> tuple[date, date]:
    if not has_catalog:
        # PR のビルド確認は直近の 1 か月だけ
        return today - timedelta(days=30), today
    # 直近の会議録だけが後から登録される。過去分の取得中は最後の開会日から続ける
    start = (
        FIRST_DAY if cursor is None
        else cursor if cursor < today - timedelta(days=REFETCH_DAYS)
        else cursor - timedelta(days=REFETCH_DAYS)
    )
    return start, min(start + timedelta(days=MAX_DAYS - 1), today)


def already_fetched(first: date, last: date, today: date, output: Path) -> bool:
    """再取得の範囲より前の月で、ファイルがもうあるか。途中で止まった手元の取得を続きから再開するため。"""
    return last < today - timedelta(days=REFETCH_DAYS) and (output / f"{first:%Y-%m}.ndjson.gz").exists()


def fetch_month(first: date, last: date, fetched_at: str, output: Path) -> int:
    rows = [json.dumps({**row, "fetched_at": fetched_at}, ensure_ascii=False) for row in speeches(first, last)]
    path = output / f"{first:%Y-%m}.ndjson.gz"
    with replacing(path) as partial, gzip.open(partial, "wt", encoding="utf-8") as f:
        f.writelines(row + "\n" for row in rows)
    logger.info("  %s〜%s: %d 発言", first, last, len(rows))
    return len(rows)


def download_kokkai(output: Path = OUTPUT) -> int:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    has_catalog = bool(os.environ.get("FDL_WORKING"))
    cursor = published_cursor()
    start, end = span_to_fetch(cursor, today, has_catalog)
    logger.info("  前回の最後の開会日 %s、%s から %s まで", cursor, start, end)
    output.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(UTC).isoformat()
    deadline = time.monotonic() + MAX_MINUTES * 60
    total = 0
    skipped = 0
    for first, last in months(start, end):
        if already_fetched(first, last, today, output):
            skipped += 1
            continue
        total += fetch_month(first, last, fetched_at, output)
        if time.monotonic() > deadline:
            # 取得済みの月までを公開し、次のビルドは公開した最後の開会日から続ける
            logger.info("  %d 分を超えたので %s までで止める", MAX_MINUTES, last)
            break
    if not has_catalog:
        # 閉会中は 1 か月以上発言の無いことがある。PR のビルド確認は、発言のある月まで
        # 1 か月ずつさかのぼる
        first = date(start.year, start.month, 1)
        for _ in range(12):
            if total:
                break
            first = (first - timedelta(days=1)).replace(day=1)
            total += fetch_month(first, next_month(first) - timedelta(days=1), fetched_at, output)
    if skipped:
        logger.info("  取得済みの %d か月を飛ばした", skipped)
    if total == 0 and not skipped:
        raise SystemExit("1 件も取得できない（API の形が変わった？）")
    return total
