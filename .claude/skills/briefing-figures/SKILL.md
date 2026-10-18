---
name: briefing-figures
description: 日次ブリーフィングの「図解」セクションを書くときに使う。記事の意図に合う図の形式（Mermaid か インライン SVG か、どの図種か）を決め、構文エラーなくレンダリングでき、GitHub と GitHub Pages の両方で破綻しない図を作る。図を描くべきか否かの判断も含む。
---

# ブリーフィングの図解

## 0. まず「図が要るか」を決める

**表・箇条書き・1段落で足りるなら描かない。**「図解省略（理由: 純粋な Tips リストのため）」と明記してよい。
図が価値を持つのは次のいずれかのときだけ:

- 要素間の **関係・順序・位置** が主題で、文章にすると読み返しが必要になる
- 記事の主張が **構造** に宿っている（階層・段階・境界・ボトルネック）
- 数値の **大小関係や推移** が論点

## 1. 形式を選ぶ

| 記事の主題 | 形式 | 具体的な図種 |
|---|---|---|
| 手順・分岐・処理の流れ | **Mermaid** | `flowchart` |
| 時間順のやりとり（人⇔エージェント⇔CI 等） | **Mermaid** | `sequenceDiagram` |
| 状態と遷移条件 | **Mermaid** | `stateDiagram-v2` |
| 役割分担が並走するプロセス | **Mermaid** | `flowchart` + `subgraph`（スイムレーン） |
| 日程・フェーズの長さ | **Mermaid** | `gantt` |
| 2軸で位置づけを比較 | **SVG** | 四象限（quadrant） |
| 成熟度・採用段階の進化 | **SVG** | Wardley マップ / 段階バー |
| 層の積み重ね（責務の分離） | **SVG** | レイヤースタック |
| 絞り込み・歩留まり | **SVG** | ファネル |
| 比較マトリクス（3項目以上×3軸以上） | **表**（図にしない） | — |
| 量の流れ・配分 | **SVG** | Sankey / 積み上げバー |
| 原因の分解 | **SVG** | フィッシュボーン |

判断軸はひとつ: **自動レイアウトで意味が壊れないか**。
Mermaid はノードの位置を自分で決められないので、「位置そのものが意味を持つ図」（四象限・Wardley・ファネル・レイヤー）は必ず SVG で描く。
逆に流れ図を SVG で手描きするのは労力の無駄なので Mermaid を使う。

1記事につき図は **1〜2点**。3点以上は入れない。

## 2. Mermaid の書き方（このリポジトリの規約）

- ノードラベルに括弧・コロン・カンマ・`#`・`&` を直接書かない。**必ず `"ダブルクォート"` で囲む**
  - 誤: `A[CI(統合)]` / 正: `A["CI 統合"]`
- 日本語ラベルは可。改行は `<br/>`
- `subgraph` の ID は英数字、表示名は `["日本語"]`
- エッジラベルは `-->|"ラベル"|` の形で引用符を付ける
- 書いたあと、ノード数が 12 を超えていないか確認する。超えたら図を 2 つに割るか、要素をまとめる

サイト側は `mermaid@11` を `htmlLabels: false` で描画する。`<br/>` 以外の HTML タグは使わない。

## 3. インライン SVG の書き方

設計規範は [diagram-design](https://github.com/cathrynlavery/diagram-design)（MIT License, © Cathryn Lavery）から引いている。
以下はこのリポジトリ向けに要約したもの。

### 複雑さの予算（超えたら削るか分割する）

| 項目 | 上限 |
|---|---|
| ノード数 | 9 |
| 矢印・遷移 | 12 |
| アクセント色を当てる要素 | 2 |
| 注釈コールアウト | 2 |

**削除優先**: 常に一緒に動くノードは1つに統合する。レイアウトから自明な矢印は消す。これ以上削れないところで止める。

### 配色（必ず CSS 変数 + フォールバックで書く）

サイトではページのテーマ変数を継承し、GitHub 上の `<img>` 表示ではフォールバック値が使われる。
**どちらでも読めるよう、必ず2つ書く。**

```
背景       fill="var(--fig-paper, #ffffff)"
面（淡）   fill="var(--fig-paper-2, #ecebe8)"
文字       fill="var(--fig-ink, #2d3142)"
補助文字   fill="var(--fig-muted, #6b6f80)"
罫線・枠   stroke="var(--fig-rule, #c4c3bf)"
アクセント fill/stroke="var(--fig-accent, #bf4520)"
強調の面   fill="var(--fig-accent-tint, #f6e3dc)"
外部リンク stroke="var(--fig-link, #2f6f8f)"
```

**アクセントは図全体で最大2要素**。主役の経路かボトルネックにだけ当てる。

### 書式ルール

- **影は使わない。** 立体感は 1px のヘアラインで出す
- 座標・幅・高さ・余白は **4px グリッド** に乗せる
- ノードの角丸は `rx="6"`、小さなタグは `rx="2"`
- フォント: 見出し `font-family="Geist, 'Noto Sans JP', sans-serif"`、
  補助・数値 `font-family="'Geist Mono', monospace"`。サイズは 11〜16px
- コネクタは **直交のみ**。斜め線を引かない。折れ曲がりは2本の直線で表現する
- 矢印ラベルは短く（全角7文字・半角14文字以内）。線の上に置くときは
  下に `fill="var(--fig-paper, #ffffff)"` の矩形を敷いて線を隠す
- 平行に走る線は 12px 以上離す
- 凡例は図の下端に横並びで置く（`viewBox` の高さを 60px ほど広げる）
- `<title>` と `<desc>` を必ず入れる。ID は図ごとのスラッグを接頭辞にする

### やってはいけないこと

- 影・グロー・グラデーション
- すべてのノードを同じ大きさの箱にする（情報量の差を形に出す）
- アクセント色を3箇所以上に使う
- Mermaid の自動レイアウトをそのまま SVG に写すこと（それなら Mermaid のままでよい）
- 図の中に浮いた凡例を置くこと

### ファイルの置き場所と参照

```
briefings/YYYY/MM/figures/DD-figN.svg
```

ブリーフィング本文からは **相対パス** で参照する（`DD.md` と同じ階層から見た `figures/`）:

```markdown
![AI-DLC の3フェーズと責務の移動](figures/18-fig1.svg)
```

- サイト生成時に SVG は HTML へインライン展開され、ページの配色変数を継承する
- GitHub の Markdown 表示では通常の画像として表示され、フォールバック色が使われる
- `width` / `height` 属性は付けず、`viewBox` だけ指定する（レスポンシブにするため）

### 雛形

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 360" role="img"
     aria-labelledby="acd-title acd-desc">
  <title id="acd-title">ACD の権限分離</title>
  <desc id="acd-desc">実装エージェントは本番昇格できず、別の検証エージェントが昇格を担う</desc>

  <rect x="0" y="0" width="720" height="360" fill="var(--fig-paper, #ffffff)"/>

  <!-- 矢印はノードより先に描く -->
  <path d="M 180 120 H 300" fill="none" stroke="var(--fig-muted, #6b6f80)"
        stroke-width="1" marker-end="url(#acd-arrow)"/>

  <rect x="60" y="96" width="120" height="48" rx="6"
        fill="var(--fig-paper-2, #ecebe8)" stroke="var(--fig-rule, #c4c3bf)" stroke-width="1"/>
  <text x="120" y="125" text-anchor="middle" font-size="13"
        font-family="Geist, 'Noto Sans JP', sans-serif"
        fill="var(--fig-ink, #2d3142)">実装エージェント</text>

  <defs>
    <marker id="acd-arrow" viewBox="0 0 8 8" refX="7" refY="4"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 8 4 L 0 8 z" fill="var(--fig-muted, #6b6f80)"/>
    </marker>
  </defs>
</svg>
```

## 4. 書いたあとの確認

```bash
# 1. SVG が XML として妥当か
python3 -c "import xml.dom.minidom,sys; xml.dom.minidom.parse(sys.argv[1]); print('XML OK')" \
  briefings/YYYY/MM/figures/DD-figN.svg

# 2. フォールバック色を書き忘れていないか（var(--fig-x) だけの箇所を洗い出す）
grep -o 'var(--fig-[a-z0-9-]*)' briefings/YYYY/MM/figures/DD-figN.svg

# 3. サイトが生成でき、図が展開されるか
python3 site/build.py
grep -c '<figure class="fig"' _site/briefings/YYYY/MM/DD.html
```

Mermaid は `site/build.py` でのビルド後、ブラウザで開いて `.mermaid-error` が出ていないことを確認する。
確認できない場合は、ノードラベルの引用符と矢印記法を目視で検算する。

## 5. diagram-design プラグインが入っている場合

`.claude/settings.json` でマーケットプレイス `diagram-design` を登録してある。
セッションでプラグインが読み込まれている場合は、その 45 種の図種リファレンスとテンプレートを使ってよい。
ただし **出力はこのリポジトリの規約に合わせる**:

- 単体の HTML ファイルではなく **`.svg` 1枚** として書き出す
- 配色はプラグイン既定のトークンではなく、上記の `var(--fig-*, #fallback)` 形式にする
- 保存先は `briefings/YYYY/MM/figures/DD-figN.svg`

プラグインが読み込まれていなくても、本スキルの規範だけで図は描ける。プラグインの有無を確認する手順は不要。
