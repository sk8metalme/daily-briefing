# Review Notes

確認日: 2026-07-12

## Addressed before repository placement

- artifactのsource registryをREADMEの一次情報と揃え、Qwen Code、Meta-Harness、Harness-Bench、Effective Harness Engineering、Fujitsu Researchを追加した。
- Claw-SWE-Benchの27.4ポイント差がQwen 3.6-flash固定の比較であり、Qwen3.6-27Bへの直接効果量ではないことを確認した。
- `preserve_thinking`、best-of-4/8、TTS@8はコストと品質の交換条件として扱い、固定budgetのローカルA/Bで測る前提を維持した。

## Remaining assumptions

- 対象hardware、inference engine、agent framework、latency target、task mixは未指定。
- Qwen3.6-27B固定でparser、edit loop、filesystem state、preserve thinkingを個別に変えた公開ablationは未確認。
