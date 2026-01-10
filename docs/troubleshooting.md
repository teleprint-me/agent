# llama.cpp

## Backend: Vulkan

### Issue: Model fails to load into memory

| date       | pull request | commit    | issue                                                |
| ---------- | ------------ | --------- | ---------------------------------------------------- |
| 2026-01-08 | #18679       | 64848deb1 | Model fails to load into memory                      |
| 2026-01-04 | #17004       | d3dce4e0a | Model loads into memory and queries fail (500 error) |
| 2026-01-04 | #18594       | 4974bf53c | Model loads into memory and accepts requests         |

### Issue: Model fails to chain tool calls

| date       | pull request | commit    | issue                                |
| ---------- | ------------ | --------- | ------------------------------------ |
| 2026-01-03 | #18566       | c69c7ebc9 | Model emits early stop, fails to chain |
|            |              |           | Model successfully chains tool calls |

#### TODO: Likely commits affecting tool calling

**potential suspects:**

- cef1d23c5 (common/grammar : replace problematic backtracking regex `[\s\S]*`
  (#18342), 2026-01-03)
- a554a1ecc (context : fix reserve token padding to n_seqs (#18536),
  2026-01-03)
- 9dba9f535 ((Bugfix, ggml-cuda) Pool alloc count fix + small size computation
  type adjustment (#18559), 2026-01-03)

**potential stability:**

- 18ddaea2a (vulkan: Optimize GGML_OP_CUMSUM (#18417), 2026-01-02)
