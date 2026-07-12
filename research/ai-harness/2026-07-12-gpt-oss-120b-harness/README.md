# gpt-oss-120b コーディング・ハーネス調査

確認日: 2026-07-12

## 技術サマリー

重みを変えずに実務コーディング性能を上げる最優先事項は、一般的なプロンプト技巧ではなく、`gpt-oss` が学習した **Harmony形式とtool loopを正しく再現すること**。その上で、課題に応じたreasoning effort、構造化された編集・テストループ、選択的コンテキスト、実行境界を段階導入する。

公式評価では、同じ `gpt-oss-120b` のSWE-bench Verifiedがreasoning lowの47.9%からhighの62.4%へ **14.5ポイント**、Aider Polyglotが24.0%から44.4%へ **20.4ポイント**上昇した。これは重み固定の直接証拠だが、推論token・遅延も増えるtest-time computeの差であり、純粋なオーケストレーション差ではない。

一方、Claw-SWE-Benchでは別モデルのGLM 5.1を固定したまま、minimal direct-diff adapterの19.1%からfull adapterの73.4%へ **54.3ポイント**上昇した。ハーネス改善余地の強い証拠だが、`gpt-oss-120b`への効果量として外挿してはいけない。

## 推奨導入順

### P0: Harmony互換性をpromotion gateにする

1. 公式 `openai-harmony` renderer/parser、または互換性が検証されたchat templateを使う。
2. `system`にはreasoning effort・日付・組み込みtool・有効channelを置き、通常の行動指示とfunction schemaは`developer`へ置く。
3. `analysis`、`commentary`、`final`を区別し、function callは原則`commentary`へ流す。
4. tool callでsamplingが止まった場合は、直前の`final`以降のanalysisとtool call/resultを次のsamplingへ戻す。`final`が出た後の次ターンでは過去analysisを落とす。
5. 保存履歴では末尾の`<|return|>`を`<|end|>`へ正規化する。`<|call|>`と`<|return|>`はdecode-time stop tokenとして扱う。
6. raw CoTはログ上でもend userへ表示しない。必要ならアクセス制御された短期traceとして保持し、保持期限を設定する。

この層が壊れていると、tool resultを踏まえた継続推論、履歴圧縮、function schemaの精度を同時に失うため、他の最適化より先に検証する。

### P1: reasoning effortを課題別にルーティングする

- `low`: ファイル列挙、既知コマンド実行、定型変換など、失敗時の回復が安い操作。
- `medium`: 通常の小規模修正と第一候補。公式既定値でもある。
- `high`: 原因が不明な障害、複数ファイルの整合修正、設計判断、回帰原因の探索。

固定でhighにするのではなく、`medium → 再現失敗/テスト失敗/同一tool失敗2回 → highで再計画`の昇格規則を比較する。公式推奨samplingは `temperature=1.0`, `top_p=1.0`。まずこの値を基準にし、sampling変更とreasoning effort変更を同じ実験セルで混ぜない。

### P2: coding toolを小さく構造化する

最小tool setは `list/search/read/line-edit-or-patch/run-command/run-tests/git-diff`。各toolは、成功・失敗、exit code、対象path、変更行数、要約済みstderrを構造化して返す。

- 編集前に対象ファイルと関連テストを読む。
- patchはモデルの最終文から抽出せず、実workspaceのGit差分から取得する。
- command outputは失敗箇所、先頭/末尾、exit codeへ圧縮し、全文はfilesystem上のartifactへ退避する。
- 同じ失敗を再実行する前に、観測と仮説を更新させる。

### P3: 編集・検証ループを状態機械にする

`reproduce → localize → smallest patch → targeted test → regression test → lint/typecheck → diff review → final`を明示的な状態として持つ。状態遷移条件をtool resultで判定し、自然言語の「たぶん成功」で完了させない。

失敗時は次の順で回復する。

1. exit codeと失敗assertionを要約する。
2. 直前の仮説と変更を比較する。
3. 同じ操作の反復ではなく、検索範囲・仮説・toolを変更する。
4. retry上限でcheckpointを保存し、high reasoningで再計画する。

### P4: コンテキストと永続状態を分離する

会話履歴へrepo全体を詰め込まず、現在の目的、触ったファイル、検証結果、未解決事項をfilesystemへ保存する。モデルへ戻すのは現在の状態、対象コード、直近の失敗、関連symbolだけにする。

Harmony固有のCoT履歴規則と、長期タスクの永続状態は別物として扱う。前者はtool call継続中だけ正確にreplayし、後者は短い構造化summaryとして次ターンへ渡す。

### P5: 実行境界と候補選択を追加する

- sandbox、network既定拒否、command timeout、秘密情報マスク、書き込み可能path制限を置く。
- 高コストlaneだけbest-of-Nを許可し、候補はunit test、lint、typecheck、patch size、禁止pathで機械選択する。
- selectorに同じモデルの自己評価だけを使わず、実行結果を主信号にする。

## 直接証拠

| 固定条件 | 変更条件 | SWE-bench Verified | Aider Polyglot | 解釈 |
|---|---|---:|---:|---|
| gpt-oss-120b / MXFP4 | Reasoning low | 47.9% | 24.0% | 低コスト基準 |
| gpt-oss-120b / MXFP4 | Reasoning medium | 52.6% | 34.2% | 公式既定 |
| gpt-oss-120b / MXFP4 | Reasoning high | 62.4% | 44.4% | low比 +14.5pt / +20.4pt |

公式モデルカードはSWE-bench Verifiedを「Codex CLIに似たterminal exec toolを持つagentic rollout」で評価している。したがって値はraw model単体ではなく、公式scaffold込みのモデル・ハーネス構成の成績である。

## 間接証拠

- Claw-SWE-Bench: GLM 5.1固定でminimal adapter 19.1%、full adapter 73.4%。full adapterはworkspace整合、prompt、patch取得・cleaningなど複数要素を同時に変えており、単一要素ablationではない。
- 同研究のQwen条件では、5 harness間の差が27.4ポイント。これはGLM 5.1のminimal/full adapter差54.3ポイントとは別の比較で、モデル選択差29.4ポイントと同程度だった。
- Harness-Bench: 106 sandboxed tasks、5,194 trajectoriesで、workspace state、tool feedback、検証可能な出力契約から推論が外れる「execution-alignment failure」を主要失敗として報告した。ただし公開本文で`gpt-oss-120b`固定の結果は確認できなかった。

## 固定モデル評価計画

### 実験セル

- A: 現行ハーネス。
- B: A + 公式Harmony renderer/parserと履歴規則。
- C: B + reasoning router（medium基準、失敗時high昇格）。
- D: C + 構造化edit/test/diff状態機械。
- E: D + filesystem stateと選択的context。
- F: E + best-of-2/4と実行結果selector（高コストlaneのみ）。

### 固定条件

同一model revision、同一MXFP4重み、同一inference engine/version、同一sampling、同一prompt corpus、同一task順、同一wall-time/token/tool-call budgetを固定する。reasoning effortを比較する実験だけは、token使用量を結果指標として記録し、同一token budget比較と実運用budget比較を分ける。

### 指標

- 主指標: task pass rate、hidden/held-out test pass rate。
- 実行品質: patch apply、tool parse error、無変更終了、禁止path変更、lint/test到達率。
- 効率: input/output/reasoning token、wall time、first-pass success、tool call数、retry数、peak VRAM。
- 信頼性: 同一失敗の反復、timeout、stale workspace参照、tool result無視、最終回答と実workspaceの不一致。

### 試験規模と判定

まず10〜15件・1 seedで壊れた構成を除外する。本試験は少なくとも30〜50件・各条件3 seed。task単位でpaired bootstrapまたは置換検定を使い、pass/failはtask内seedを事前定義した規則で集約してからMcNemarを使う。改善採用条件は、pass rateの改善だけでなく、parse error・禁止変更・コストのguardrailを満たすこと。

## 制約と未確定事項

- `gpt-oss-120b`を固定してHarmony実装、tool schema、編集primitive、state管理を個別に変えた公開ablationは確認できなかった。
- reasoning effortの改善はtest-time compute増加を含むため、無料のハーネス改善ではない。
- reasoning router自体の公開検証は確認できていない。公式証拠が直接支持するのはreasoning effort別スコア差であり、`medium → 失敗時high`の昇格規則はローカルA/Bで検証する仮説として扱う。
- Claw-SWE-Benchの大きなadapter差は別モデルで、複数変更を含む。
- 120Bの公式目安はMXFP4で60GB以上、単一80GB級GPUまたはmulti-GPU。Apple Silicon向けreference Metal実装は公式にproduction-readyではない。hardware、runtime、量子化、並列方式が未指定なので、性能・速度の絶対値は手元測定が必要。
- raw CoTはdebugに有用でもend user表示は不適切。保存する場合は秘密情報・個人情報の混入を前提に保護する。

## 次の実装タスク

1. Harmony transcript conformance testを作り、tool call後のanalysis保持とfinal後の破棄をfixtureで固定する。
2. 10〜15件のprivate coding task setを作り、A/B/Cを先に比較する。
3. CがBを上回った場合だけedit/test状態機械Dを実装し、変更ごとに寄与を分離する。
4. 実運用traceからtool parse error、反復失敗、stale stateを自動集計する。

## 一次情報

- [OpenAI gpt-oss model card](https://arxiv.org/html/2508.10925)
- [OpenAI Harmony response format](https://developers.openai.com/cookbook/articles/openai-harmony)
- [OpenAI: raw CoT handling](https://developers.openai.com/cookbook/articles/gpt-oss/handle-raw-cot)
- [OpenAI: gpt-oss with vLLM](https://developers.openai.com/cookbook/articles/gpt-oss/run-vllm)
- [OpenAI gpt-oss repository](https://github.com/openai/gpt-oss)
- [Claw-SWE-Bench](https://arxiv.org/html/2606.12344)
- [Harness-Bench](https://arxiv.org/html/2605.27922)
