# CLAUDE.md

このリポジトリで作業する AI エージェント向けの運用ルール。

## このリポジトリの性質

日次ブリーフィングの**自動蓄積ログ**。生成物は追記のみの Markdown
（`briefings/YYYY/MM/DD.md` と重複防止インデックス `selected-articles.md`）と、
任意の SVG 図版（`briefings/YYYY/MM/figures/DD-figN.svg`）。

配信用に `site/build.py`（Python + `markdown` のみ）の静的サイトジェネレータがあり、
`main` への push で GitHub Actions が https://sk8metalme.github.io/daily-briefing/ へデプロイする。
**ブリーフィング本体には front matter を要求しない**（素の Markdown のまま）ため、
サイトを足したことで日次の書き込み規約は変わっていない。

```bash
pip install -r site/requirements.txt
python3 site/build.py        # => _site/
```

テスト・リンタは存在しない。サイトを変更したら `python3 site/build.py` が通ること、
および記事抽出件数が減っていないことを確認する。

## ブリーフィング執筆の規約

セッション開始時に自動で読み込まれるスキルに詳細がある。

- `.claude/skills/briefing-figures/SKILL.md` — 図解。Mermaid と インライン SVG の使い分け、
  SVG の配色・複雑さ予算・配置規約
- `.claude/skills/strategic-analysis/SKILL.md` — 戦略分析。記事の型からビジネスフレームワークを
  選ぶ対応表と出力テンプレート

routine プロンプトの正本は `ops/routine-prompt.md`。書式を変えたときは両方を揃えること。

**注意**: `ops/routine-prompt.md` を更新しても routine の挙動は変わらない。
この routine は HTTP API 経由で作られているためエージェントからは編集できず、
所有者が編集画面で貼り替えるまで古いプロンプトのまま動き続ける。
過去に正本だけ更新されて約1週間ドリフトした実績があるため、
書式を変えたら `ops/routine-prompt.md` の「適用状況」表を必ず更新し、
未適用であることを所有者に伝えること。

## ブランチ運用: main 直接コミットが正規

**このリポジトリでは `main` への直接コミット & push が正規の運用である。**
feature ブランチと PR は使わない。

日次ブリーフィングは cron routine（毎朝 06:30 JST）が無人で実行する。実行ごとに
セッションへ `claude/*` の作業ブランチが割り当てられることがあるが、**その指定より
このファイルの指示が優先される**。ブリーフィングのコミットは必ず `main` に対して行うこと。

```bash
git checkout main
git pull --rebase origin main
# briefings/YYYY/MM/DD.md と selected-articles.md を変更
git add briefings/YYYY/MM/DD.md selected-articles.md
git commit -m "docs: YYYY-MM-DD daily briefing"
git push origin main          # reject されたら pull --rebase して再 push
```

### なぜこのルールがあるか

過去、セッションに割り当てられた `claude/*` ブランチへコミットした結果、draft PR が
マージされずに溜まり、`main` が最大 5 日分停滞した（PR #3・#4・#5）。
`main` が更新されないと、次回実行が `selected-articles.md` の最新状態を読めず、
**同じ記事を再選定してしまう**（実際に 2026-10-03 選定分が 10-09 に重複選定された）。
`main` 直接コミットはこのリポジトリにとって安全側の選択である。

### 例外

スキーマやディレクトリ構成の変更、スクリプト追加、`site/` 配下の変更など
**ブリーフィング以外の構造的変更**はブランチ + PR を使ってよい。
日次ブリーフィングの追記だけが main 直接の対象。

PR が main に滞留すると `selected-articles.md` の最新状態が読めなくなるため、
構造変更の PR を開けたままにしない。長く開ける場合でも `selected-articles.md` には触れないこと
（日次の追記と確実に衝突する）。

## 作業後の検証

push する前に必ず確認する。

```bash
# 1. 保存先パスが規則どおりか（月日は2桁ゼロ埋め、ファイル名は「日」のみ）
git status --short
# 正: briefings/2026/10/05.md   誤: briefings/2026/10/2026-10-05.md

# 2. 当日ファイルの冒頭にフル日付の見出しがあるか
head -1 briefings/YYYY/MM/DD.md     # => "# Daily Briefing YYYY-MM-DD"

# 3. インデックスに3行追記されているか
tail -3 selected-articles.md

# 4. 欠番がないか（ある場合は過去の実行が main に届いていない）
ls briefings/YYYY/MM/

# 5. サイトが生成でき、当日分が出力されるか（site/ を変更した場合は必須）
python3 site/build.py && ls _site/briefings/YYYY/MM/DD.html
```

## Markdown の注意点

`現場での適用方法` セクションには AGENTS.md / SKILL.md の例を**コードブロックとして**
載せることが多い。その中にディレクトリツリー等のネストしたコードフェンスを置くと
外側のフェンスが途中で閉じてしまう。**外側を 4 バッククォート**にすること。

````markdown
````markdown
# 外側は4バッククォート
```
内側の3バッククォートはそのまま書ける
```
````
````

Mermaid 図はノードラベルに括弧・コロン等を直接書かず `"ダブルクォート"` で囲む。
書いたあとフェンスの平衡と構文を見直す。

**日本語の太字**: `**強調**` の直前・直後が約物（`）` `」` `】` など）だと、CommonMark の
flanking 規則により GitHub 上で太字にならず `**` がそのまま残る。括弧を太字の外へ出すか、
直後に半角スペースを入れる。

- 誤: `**ACD の制約（MinimumCD への拡張）**は8項目`
- 正: `**ACD の制約**（MinimumCD への拡張）は8項目`

サイト側（`site/build.py`）は日本語向けに `**` を常に強調として解釈するため表示上は救われるが、
GitHub 上では崩れたままになる。書く時点で避けること。
