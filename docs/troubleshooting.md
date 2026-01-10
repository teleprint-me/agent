# llama.cpp

## Backend: Vulkan

### Issue: Model fails to load into memory

| date       | pull request | commit    | issue |
| ---------- | ------------ | --------- | ----- |
| 2026-01-04 | #18594       | 4974bf53c | Model loads into memory and accepts requests | 
| 2026-01-04 | #17004       | d3dce4e0a | Model loads into memory and queries fail (500 error) |
| 2026-01-08 | #18679       | 64848deb1 | Model fails to load into memory |

### Issue: Model fails to chain tool calls

| date       | pull request | commit    | issue |
| ---------- | ------------ | --------- | ----- |
|            |              |           | Model successfully chains tool calls |
| 2026-01-03 | #18566       | c69c7ebc9 | Model emits early stop |
