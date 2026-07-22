# Running the LLM via vLLM

SRIS uses a local LLM for answer evaluation. The evaluation provider is `local_vllm`, which connects to an OpenAI-compatible vLLM server running on the same machine.

## Prerequisites

- 2x NVIDIA RTX 4090 (24 GB each) — one for vLLM, one for the model
- conda env `sris` with vLLM installed
- Model checkpoint at `/home/mrazek/SRIS/models/qwen3-8b-awq`

## Start the vLLM Server

```bash
CUDA_VISIBLE_DEVICES=1 /home/ubuntu/anaconda3/envs/sris/bin/python \
  -m vllm.entrypoints.openai.api_server \
  --host 0.0.0.0 \
  --port 8100 \
  --model /home/mrazek/SRIS/models/qwen3-8b-awq \
  --served-model-name qwen3-8b-awq \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.60 \
  --max-num-seqs 8 \
  --trust-remote-code
```

**Flags explained:**

| Flag | Value | Reason |
|---|---|---|
| `CUDA_VISIBLE_DEVICES=1` | GPU 1 | Leave GPU 0 free for other work |
| `--port 8100` | vLLM API | Matches `LOCAL_LLM_BASE_URL=http://localhost:8100/v1` |
| `--max-model-len 4096` | 4K context | Balances memory vs capacity |
| `--gpu-memory-utilization 0.60` | 60% VRAM | Leaves headroom for KV cache |
| `--max-num-seqs 8` | 8 concurrent | Prevents OOM during batch eval |
| `--trust-remote-code` | required | Needed for Qwen3 custom code |

## Verify

```bash
curl http://localhost:8100/v1/models
```

Expected: `{"object":"list","data":[{"id":"qwen3-8b-awq",...}]}`

## Connect SRIS Backend

Set these env vars when starting the backend:

```bash
export EVALUATION_PROVIDER=local_vllm
export LOCAL_LLM_BASE_URL=http://localhost:8100/v1
export LOCAL_LLM_MODEL=qwen3-8b-awq
```

## Available Models

| Path | Format |
|---|---|
| `/home/mrazek/SRIS/models/qwen3-8b-awq` | AWQ quantized (safetensors) |
| `/home/mrazek/SRIS/models/qwen3-8b-gguf` | GGUF format (for llama.cpp) |

## Troubleshooting

- **Port in use**: `ss -tlnp | grep 8100` then `kill <pid>`
- **OOM**: Reduce `--gpu-memory-utilization` or `--max-model-len`
- **`'FieldInfo' object has no attribute 'init'`**: Upgrade pydantic — `pip install --upgrade pydantic`
- **Model load timeout**: First load takes 30–60s; subsequent loads use disk cache
