# daily-briefing

AI活用・開発ツール・生産性向上に関する技術記事の日次ブリーフィングを自動蓄積するリポジトリ。

**📖 読む: https://sk8metalme.github.io/daily-briefing/**

## 概要

Claude Code のクラウドroutine（cronスケジュールされたエージェント）が毎朝 6:00 JST に実行され、以下を行う：

1. 対象トピックの新着記事・研究・実践レポートを世界中から調査
2. 実業務で再現可能な「実践知」を重視して3件を選定（過去選定分と重複しない）
3. 各記事を日本語で要約し、`briefings/YYYY/MM/DD.md` に保存
4. `selected-articles.md`（重複防止インデックス）に選定記事を追記
5. main ブランチに直接コミット & push

## 対象トピック

- AI活用
- 開発ツール
- 生産性向上
- ハーネスエンジニアリング
- ループ設計
- コンテキストエンジニアリング
- コンテキスト節約
- ローカルLLM

## ディレクトリ構成

```
briefings/
  YYYY/                 # 年（例: 2026）
    MM/                 # 月（2桁ゼロ埋め、例: 09）
      DD.md             # 日（2桁ゼロ埋め、例: 22.md）— 日次ブリーフィング
      figures/          # 任意。手描きの SVG 図版
        DD-figN.svg
selected-articles.md    # 選定済み記事インデックス（重複防止用）
site/                   # 静的サイトジェネレータ（GitHub Pages 用）
  build.py
  about.md
  assets/
ops/routine-prompt.md   # routine の保存プロンプトの正本
.claude/skills/         # 執筆規約（セッション開始時に自動で読み込まれる）
```

例: 2026年9月22日分は `briefings/2026/09/22.md`。
日付はファイル冒頭の見出し（`# Daily Briefing YYYY-MM-DD`）にも記載する。

## ブリーフィングのフォーマット

各記事につき以下を記載：

- タイトル（原題 + 日本語訳）
- URL / 公開日 / 著者・媒体
- 本文翻訳
- 重要ポイント
- 図解（Mermaid / インライン SVG）
- 戦略分析（ビジネスフレームワークによる構造化）
- 現場での適用方法
- 期待効果
- 注意点

執筆規約は `.claude/skills/` 配下に置いてある。

| スキル | 内容 |
|---|---|
| `briefing-figures` | 図解。Mermaid と SVG の使い分け、SVG の配色・複雑さ予算・配置規約 |
| `strategic-analysis` | 戦略分析。記事の型からフレームワークを選ぶ対応表と出力テンプレート |

### 図解の方針

- **Mermaid** — 処理フロー・シーケンス・状態遷移など、手順や時間順序が主題のとき。
  GitHub の Markdown 上でもそのまま描画される
- **インライン SVG** — 四象限・Wardley マップ・レイヤースタック・ファネルなど、
  位置そのものが意味を持つとき。Mermaid の自動レイアウトでは表現できないため手で描く

SVG の設計規範（ノード上限9・アクセント1色・影を使わず 1px ヘアライン・4px グリッド・直交コネクタ）は
[diagram-design](https://github.com/cathrynlavery/diagram-design)（MIT License, © Cathryn Lavery）から
引いたもので、サイト自体の配色・余白設計にも同じトークンを使っている。

プラグインとして使う場合は `.claude/settings.json` にマーケットプレイス登録済み。
未インストールでも `briefing-figures` スキルだけで図は描ける。

## サイトをローカルでビルドする

```bash
pip install -r site/requirements.txt
python3 site/build.py          # => _site/
npx http-server _site -p 8080  # http://127.0.0.1:8080
```

`main` への push で `.github/workflows/pages.yml` が走り、GitHub Pages へ自動デプロイされる。
ブリーフィング本体は front matter を持たない素の Markdown のままで、
ジェネレータ側が解析している（routine の書き込み規約は変えていない）。

初回のみ、リポジトリの **Settings → Pages → Source** を `GitHub Actions` に設定する必要がある。

## 運用メモ

- このリポジトリは自動蓄積ログ用のため、例外的に main への直接コミット運用とする
- routine の管理: https://claude.ai/code/routines
