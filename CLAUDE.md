# CLAUDE.md

このリポジトリで作業する AI エージェント向けの運用ルール。

## このリポジトリの性質

日次ブリーフィングの**自動蓄積ログ**。コードを持たず、生成物は追記のみの Markdown
（`briefings/YYYY/MM/DD.md` と重複防止インデックス `selected-articles.md`）。
ビルド・テスト・リンタは存在しない。

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

スキーマやディレクトリ構成の変更、スクリプト追加など**ブリーフィング以外の構造的変更**は
ブランチ + PR を使ってよい。日次ブリーフィングの追記だけが main 直接の対象。

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
