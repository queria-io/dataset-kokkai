"""国会会議録検索システムの検索用 API から、発言を 1 件ずつ取り出す。

発言単位出力（/api/speech）を、開会日（from・until）で 1 か月ずつに絞って取る。1 回で
返るのは 100 件までなので、nextRecordPosition をたどってページを送る。

会議録は開会から数週間〜数か月たって登録される。毎回、公開中の表の最後の開会日から
REFETCH_DAYS 日前までさかのぼって取り直す。初回と過去分は MAX_DAYS 日ずつ進める。

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
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from shared.fetch import fetch, replacing

logger = logging.getLogger("pipelines")

API = "https://kokkai.ndl.go.jp/api/speech"
USER_AGENT = "dataset-ndl (+https://github.com/queria-io/dataset-ndl)"
OUTPUT = Path("data/kokkai/speeches")
# 第 1 回国会の開会日
FIRST_DAY = date(1947, 5, 20)
REFETCH_DAYS = 180
MAX_DAYS = int(os.environ.get("KOKKAI_MAX_DAYS", "1100"))
PAGE_SIZE = 100
# 利用条件は短時間の大量アクセスを控えるよう求めている。1 回ずつ間を空ける
INTERVAL_SECONDS = 1.0


def page(start: date, end: date, record: int) -> dict:
    query = urlencode(
        {"from": start.isoformat(), "until": end.isoformat(), "startRecord": record,
         "maximumRecords": PAGE_SIZE, "recordPacking": "json"}
    )
    body = json.loads(fetch(f"{API}?{query}", user_agent=USER_AGENT))
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
    """公開中の kokkai.speeches の最後の開会日。FDL_WORKING が無いか、表がまだ無ければ None。"""
    working = os.environ.get("FDL_WORKING")
    if not working:
        return None
    import duckdb

    con = duckdb.connect(config={"custom_user_agent": os.environ.get("QUERIA_USER_AGENT", "")})
    con.execute("INSTALL ducklake; LOAD ducklake; INSTALL httpfs; LOAD httpfs;")
    con.execute(f"ATTACH 'ducklake:{working.replace(chr(39), chr(39) * 2)}' AS previous (READ_ONLY, META_TYPE 'sqlite')")
    try:
        return con.sql("select max(date) from previous.kokkai.speeches").fetchall()[0][0]
    except duckdb.CatalogException as error:
        logger.info("  公開中の表が無い: %s", error)
        return None
    finally:
        con.close()


def span_to_fetch(cursor: date | None, today: date, has_catalog: bool) -> tuple[date, date]:
    if not has_catalog:
        # PR のビルド確認は直近の 1 か月だけ
        return today - timedelta(days=30), today
    start = max(FIRST_DAY, cursor - timedelta(days=REFETCH_DAYS)) if cursor else FIRST_DAY
    return start, min(start + timedelta(days=MAX_DAYS - 1), today)


def download_kokkai(output: Path = OUTPUT) -> int:
    today = datetime.now(ZoneInfo("Asia/Tokyo")).date()
    cursor = published_cursor()
    start, end = span_to_fetch(cursor, today, bool(os.environ.get("FDL_WORKING")))
    logger.info("  前回の最後の開会日 %s、%s から %s まで", cursor, start, end)
    output.mkdir(parents=True, exist_ok=True)
    fetched_at = datetime.now(UTC).isoformat()
    total = 0
    for first, last in months(start, end):
        rows = [json.dumps({**row, "fetched_at": fetched_at}, ensure_ascii=False) for row in speeches(first, last)]
        path = output / f"{first:%Y-%m}.ndjson.gz"
        with replacing(path) as partial, gzip.open(partial, "wt", encoding="utf-8") as f:
            f.writelines(row + "\n" for row in rows)
        total += len(rows)
        logger.info("  %s〜%s: %d 発言", first, last, len(rows))
    if total == 0:
        raise SystemExit("1 件も取れない（API の形が変わった？）")
    return total
