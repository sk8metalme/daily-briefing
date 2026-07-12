# Sources

確認日: 2026-07-12

## Primary sources

- Qwen3.6-27B official model card: https://huggingface.co/Qwen/Qwen3.6-27B
- Qwen Code official repository: https://github.com/QwenLM/qwen-code
- Claw-SWE-Bench: https://arxiv.org/html/2606.12344
- Meta-Harness: https://arxiv.org/html/2603.28052
- Harness-Bench: https://arxiv.org/html/2605.27922
- Effective Harness Engineering: https://arxiv.org/html/2605.15221
- Fujitsu Research Qwen3.5-27B multi-agent harness: https://blog-en.fltech.dev/entry/2026/04/07/swebench

## Notes

- Qwen3.6-27B固定でハーネスだけを変えた公開ablationは未確認。
- Claw-SWE-Benchの27.4ポイント差はQwen 3.6-flash固定のハーネス比較で、27Bへの改善幅ではない。
- Fujitsu ResearchのQwen3.5-27B結果はTTS@8であり、Pass@1や低コスト実行とは分けて扱う。
