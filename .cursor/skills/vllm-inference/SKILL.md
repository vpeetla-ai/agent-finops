---
name: vllm-inference
description: >-
  Reason about LLM serving: PagedAttention, continuous batching, KV cache
  budget, prefill vs decode, quantization. Use when sizing GPUs, explaining
  inference costs, or integrating vllm-architecture-lab concepts.
---

# vLLM Inference

## Must know (Principal / FDE interviews)

1. **PagedAttention** — non-contiguous KV pages; ~4% waste vs ~60% contiguous
2. **Continuous batching** — per-step slot reuse → 3–4× vs static batching
3. **KV budget** — `(gpu_mem × util − weights) / (block_size × kv_per_token)`
4. **Prefill** = compute-bound; **decode** = bandwidth-bound
5. **AWQ/FP8** — quality vs throughput trade-offs

## Org reference

- Repo: [vllm-architecture-lab](https://github.com/vpeetla-ai/vllm-architecture-lab)
- Demo: https://vllm-architecture-lab.vercel.app
- API: https://vllm-architecture-lab-api.onrender.com

## When to use upstream vLLM

Production inference → [vllm-project/vllm](https://github.com/vllm-project/vllm).  
Our lab is **educational simulator** — scheduler + block allocator, not CUDA kernels.

## Integration ideas

- VAP model router: document when to route to self-hosted vLLM vs API
- AegisAI gateway: wrap `/v1/completions` for policy + audit
- LoopForge: tune `max_num_seqs`, `gpu_memory_utilization` via harness
