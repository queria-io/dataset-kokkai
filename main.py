"""国立国会図書館が公開するデータのパイプライン。

1. kokkai: 国会会議録検索システムの検索用 API から発言を取り出す
2. dbt: まだ無い会議と発言を追記する
"""

import logging

from dbt.cli.main import dbtRunner

from pipelines.kokkai import download_kokkai

# dbt を読み込むとルートロガーが先に設定されるので、force で上書きする
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
logger = logging.getLogger("pipelines")


def dbt_build():
    dbt = dbtRunner()
    for command in (["deps"], ["build"], ["docs", "generate"]):
        if not dbt.invoke(command).success:
            raise SystemExit(f"dbt {' '.join(command)} failed")


def download() -> None:
    logger.info("1/2: kokkai (国会会議録)")
    download_kokkai()


def main():
    download()
    logger.info("2/2: dbt build")
    dbt_build()


if __name__ == "__main__":
    main()
