# PaperAgent

指定キーワードに基づいて論文を調査し、日本語レポートを作成するリポジトリです。

## ディレクトリ構成

- `reports/` — 調査レポート（`YYYY-MM-DD_キーワード.md` 形式）
- `agent_instruction.md` — 論文調査エージェントへの指示
- `search_arxiv.py` — [arXiv](https://arxiv.org/) 検索スクリプト
- `search_scholar.py` — [Google Scholar](https://scholar.google.jp/) 検索スクリプト（被引用数付き）
- `search_papers.py` — arXiv / Google Scholar を統合して検索・候補抽出
- `search_connected_papers.py` — [Connected Papers](https://www.connectedpapers.com/) 関連論文取得

## セットアップ

```bash
pip install -r requirements.txt
```

Connected Papers API を使う場合は、環境変数 `CONNECTED_PAPERS_API_KEY` を設定してください。未設定の場合は Connected Papers URL の生成と Semantic Scholar による論文特定のみ行います。

## 検索例

```bash
python search_arxiv.py "multi-agent network"
python search_scholar.py "multi-agent network"
python search_papers.py "multi-agent network"
python search_connected_papers.py "Attention Is All You Need"
```

レポートには各論文の **発表元（査読付き）**、**被引用数**（Google Scholar）、**Citations**（Connected Papers）、および Citations 順の関連論文 5 件を必ず記載します。調査完了後は `agent_instruction.md` の「GitHub への反映（必須）」に従い、commit / push / PR まで行います。

## レポート一覧

| 日付 | テーマ | ファイル |
|------|--------|---------|
| 2026-07-11 | AIエージェントの発展に伴うネットワーク影響 | [reports/2026-07-11_AIエージェントNW影響.md](reports/2026-07-11_AIエージェントNW影響.md) |
