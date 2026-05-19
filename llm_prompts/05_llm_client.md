# LLM 客户端全局 Prompt 原文

> 来源文件：`overall_situation_agent/llm_client.py`

---

## 1. 全局注入的 System Prompt

**源码位置：** 第 57-60 行

这个 system prompt 会在 `chat()` 方法中**自动注入到每一次 LLM 调用**的最前面，无论调用方是否传了 system message：

```python
answer_only_system = {
    "role": "system",
    "content": "直接输出最终答案，不要输出思考过程、分析步骤或自我说明。",
}
```

`effective_messages = [answer_only_system, *messages]`

因此，项目中所有 LLM 调用实际发送的 messages 列表结构都是：

```python
[
    {"role": "system", "content": "直接输出最终答案，不要输出思考过程、分析步骤或自我说明。"},
    ...调用方传入的 messages（可能包含自己的 system）...
]
```