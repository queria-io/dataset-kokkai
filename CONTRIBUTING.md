# ビルドと更新

データセットの概要は [README.md](README.md) にあります。ここにはこのリポジトリでデータセットをビルド・更新する手順を書きます。

## ビルド

```bash
uv sync
scripts/build.sh
```

取得の間隔は 1 秒です。1 回のビルドで取得するのは前回の続きから 1,100 日分（`KOKKAI_MAX_DAYS`）までで、100 分（`KOKKAI_MAX_MINUTES`）を超えたら取得済みの月までで止めます。1947 年からすべてを取得するときは手元で `KOKKAI_MAX_DAYS=40000 KOKKAI_MAX_MINUTES=2000 scripts/build.sh` を実行します。
