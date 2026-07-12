# Qwen3.6-27B コーディング・ハーネス調査

確認日: 2026-07-12

## 結論

最優先は、Qwen公式の parser / sampling / thinking 設定を正しく通したうえで、実ファイル編集と Git patch 抽出を含む反復型ハーネスを比較導入すること。Qwen 3.6-flash を固定した Claw-SWE-Bench では、ハーネスだけで解決率が 38.6% から 66.0% まで変わった。ただし 27B の直接比較ではないため、27Bでの改善幅は手元の固定課題で測定する。

## 推奨構成

1. vLLM 0.19.0 以上で `--reasoning-parser qwen3 --enable-auto-tool-choice --tool-call-parser qwen3_coder` を使用する。テキスト専用なら `--language-model-only` も比較する。
2. coding の基準値は thinking mode、`temperature=0.6`, `top_p=0.95`, `top_k=20`。長い agent session では `preserve_thinking=true` を比較する。
3. `read/search/line-edit/run-tests/git-diff` を構造化ツールとして提供し、実ファイル編集後に Git から patch を抽出する。根拠研究の比較は workspace 整合、prompt、patch cleaning 等も同時変更しており、Git抽出単独の効果ではない。
4. `再現 → 原因特定 → 最小修正 → 対象test → regression test → lint → diff review` を状態機械にする。
5. 長い出力は exit code、失敗箇所、末尾へ圧縮し、永続状態は filesystem に保存する。repo 全体を毎回プロンプトへ入れない。
6. 高品質・非対話モードに限り best-of-4/8 と実行テストによる selector を追加する。Qwen3.5-27Bの74.8%はTTS@8で、Pass@1ではなく最大約8倍の候補生成費用を伴う。
7. sandbox、network無効化、command timeout、秘密情報マスク、変更可能パス制限を実行境界に置く。

## 評価計画

- 同一量子化、同一サーバー、同一 token/time/tool-call budget を固定する。
- A: raw chat、B: 公式 parser + tool loop、C: B + structured edit/test loop、D: C + filesystem state、E: D + preserve thinking を比較する。
- 指標: task pass、patch apply、tool parse error、lint/test到達、総token、wall time、peak VRAM、retry回数。
- まず10〜15件・1seedで候補をスクリーニングし、本試験は30〜50件・各条件3seed。task単位の階層bootstrapまたは置換検定を使い、McNemarはseed集約後に限る。

## 制約

- Qwen3.6-27Bそのものを固定してハーネスだけを変えた公開アブレーションは確認できなかった。
- Claw-SWE-Bench の直接証拠は Qwen 3.6-flash で、各セル1試行。
- Qwen公式ベンチ値は内部scaffold込みであり、raw modelの値ではない。
- `preserve_thinking` は公式推奨候補だが、長い履歴での品質・token・KV cache効果は27Bローカル環境で実測が必要。

## 一次情報

- [Qwen3.6-27B 公式モデルカード](https://huggingface.co/Qwen/Qwen3.6-27B)
- [Qwen Code 公式リポジトリ](https://github.com/QwenLM/qwen-code)
- [Claw-SWE-Bench](https://arxiv.org/html/2606.12344)
- [Meta-Harness](https://arxiv.org/html/2603.28052)
- [Harness-Bench](https://arxiv.org/html/2605.27922)
- [Effective Harness Engineering](https://arxiv.org/html/2605.15221)
- [Fujitsu Research: Qwen3.5-27B + multi-agent harness](https://blog-en.fltech.dev/entry/2026/04/07/swebench)
