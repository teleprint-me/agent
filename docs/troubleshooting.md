# llama.cpp

## Backend: Vulkan

### Issue: Model fails to load into memory

| date       | pull request | commit    | issue                                                |
| ---------- | ------------ | --------- | ---------------------------------------------------- |
| 2026-01-08 | #18679       | 64848deb1 | Model fails to load into memory                      |
| 2026-01-04 | #17004       | d3dce4e0a | Model loads into memory and queries fail (500 error) |
| 2026-01-04 | #18594       | 4974bf53c | Model loads into memory and accepts requests         |

### Issue: Model fails to chain tool calls

| date       | pull request | commit    | issue                                  |
| ---------- | ------------ | --------- | -------------------------------------- |
| 2026-01-03 | #18566       | c69c7ebc9 | Model emits early stop, fails to chain |
|            |              |           | Model successfully chains tool calls   |

- b7622 (c69c7ebc9): Verfied to be problematic?
- b7607 (ced765be4): Any commit after this is affected?

**resultant bug:**

**Description:** The model prepares to call a tool and fails after a succeeding for a few rounds.

```sh
thinking
We have snippet of main. Good.

Now read README.md top lines to give context.

completion


metrics:
  prompt tokens    +177
  generated tokens +22
  total: 9817/131072
```

#### TODO: Likely commits affecting tool calling

I'm unable to reproduce in commit af1e8e1a6.

**commits to investigate:**

- [x] c69c7ebc9 (graph : fix graph reuse logic when `n_pos_per_embd > 1` (#18566), 2026-01-03)
- [x] 18ddaea2a (vulkan: Optimize GGML_OP_CUMSUM (#18417), 2026-01-02)
- [ ] 706e3f93a (vulkan: Implement mmvq for iq1_s/iq1_m (#18450), 2026-01-02)
- [ ] 5755e52d1 (model : Maincoder-1B support (#18534), 2026-01-03)
- [ ] f38de1634 (metal : adjust extra size for FA buffer to avoid reallocations (#18545), 2026-01-02)
- [ ] af1e8e1a6 (graph : reduce topology branching (#18548), 2026-01-02)
- [ ] d84a6a98b (vocab : reduce debug logs about non-EOG control tokens (#18541), 2026-01-02)
- [ ] c6f0e832d (rpc : use unordered_map::reserve and emplace (#18513), 2026-01-02)
- [ ] e86f3c222 (cuda : fix copy of large tensors (ggml_nbytes <= INT_MAX assertion) (#18433), 2026-01-02)
- [ ] 169ee68ff (model : remove modern-bert iswa template (#18529), 2026-01-02)
- [ ] ced765be4 (model: support youtu-vl model (#18479), 2026-01-02)
- [ ] 3ccccc83f (Add conversion support for IQuestCoderForCausalLM (#18524), 2026-01-01)
- [ ] d0a6a3147 (model : add support for JinaBertModel with non-gated ffn (#18475), 2026-01-02)
- [ ] 2b2afade9 (convert : fix encoding of WPM vocab for BERT models (#18500), 2026-01-02)
- [ ] f4f501925 (model: add Solar Open model (#18511), 2026-01-02)
