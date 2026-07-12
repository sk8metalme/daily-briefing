# Review Notes

確認日: 2026-07-12

## Addressed before repository placement

- READMEとartifactの優先順位をP0〜P5で整合させた。
- Harmony履歴規則で、tool call後の継続samplingにanalysis、tool call、tool resultを戻すことを明記した。
- reasoning routerの確度を弱め、公式証拠が直接支持するのはreasoning effort別スコア差であり、`medium -> failure -> high`の昇格規則はローカルA/B対象だと明記した。
- Claw-SWE-Benchの27.4ポイント差はQwen条件の5 harness比較であり、GLM 5.1のminimal/full adapter差54.3ポイントとは別だと明記した。
- artifactのsource registryにraw CoT、vLLM、gpt-oss repository、Harness-Benchを追加した。

## Remaining assumptions

- 対象hardware、inference engine、agent framework、latency target、task mixは未指定。
- `gpt-oss-120b`固定でHarmony実装、tool schema、編集primitive、state管理を個別に変えた公開ablationは未確認。
