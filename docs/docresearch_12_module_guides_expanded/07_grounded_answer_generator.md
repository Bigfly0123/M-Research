# 07｜Grounded Answer Generator 详细设计与实施指导


> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。  
> 目标不是普通 RAG 问答，而是围绕**上下文规划、图增强检索、证据组合、自动评测、可追踪修复**构建一个小而硬的高级项目。

> 阅读方式：先看“原理知识”，再看“设计方案”，最后按“实施步骤”和“验收标准”落地。每个模块都要进入 trace 和 eval，不要只停留在概念。


## 1. 模块一句话定义

**Grounded Answer Generator** 是 DocResearch-Agent 的 **基于证据的答案生成层**。严格基于 evidence pack 生成带 citation 的答案，不允许无证据强答。

## 2. 这个模块解决什么问题

在普通 RAG 中，这一层通常被简化或省略，导致系统虽然能回答，但很难解释为什么这样回答、为什么失败、如何修复。这个模块要把“看起来能用”的 demo 变成可追踪、可调试、可评测的工程系统。

它解决的典型问题包括：

1. 模块输入输出不清晰，后续节点只能靠猜。  
2. 中间决策没有 trace，失败时无法定位。  
3. 只写概念，没有 schema、fallback 和 eval。  
4. 模块之间耦合太深，后续难以替换模型、检索策略或 prompt。  

## 3. 需要先理解的知识点

### 3.1 Grounded generation

Grounded generation：答案只能来自证据。

### 3.2 Citation granularity

Citation granularity：引用应该对应核心结论。

### 3.3 Abstention

Abstention：证据不足时要明确说不确定。

### 3.4 Answer schema

Answer schema：结构化答案方便后续 Judge。



## 4. 技术参考链接

- OpenAI text generation: https://platform.openai.com/docs/guides/text-generation
- DeepEval: https://docs.confident-ai.com/
- Ragas faithfulness: https://docs.ragas.io/

## 5. 在系统中的位置

```text
Context Planner
  -> Contextual / Structure-aware Chunker
  -> Tool Registry
  -> Hybrid + Graph Retriever
  -> Retrieval Evaluator
  -> Evidence Composer
  -> Grounded Answer Generator
  -> Self-Reflection Judge
  -> Citation Guardrails
  -> Corrective Repair Router
  -> Trace + Eval Runner
  -> Skill Prompt Registry
```

当前模块 **Grounded Answer Generator** 必须遵守三个原则：输入输出结构化、关键决策写入 trace、不抢其他模块职责。

## 6. 输入输出设计

### 6.1 通用输入

```python
class ModuleInput(BaseModel):
    question: str | None = None
    context_plan: dict | None = None
    chunks: list[dict] = []
    candidates: list[dict] = []
    evidence_pack: list[dict] = []
    answer: str | None = None
    judge_result: dict | None = None
    config: dict = {}
```

### 6.2 通用输出

```python
class ModuleOutput(BaseModel):
    status: Literal['ok', 'warn', 'fail'] = 'ok'
    data: dict = {}
    trace: dict = {}
    next_action: str | None = None
```

真实实现时建议每个模块单独建 schema，不要让 dict 满天飞。

## 7. 详细设计方案

### 7.1 设计目标

本模块要完成一个“完整 MVP”，不是论文级复刻。完整 MVP 的意思是：能独立运行、能接入 AgentState、有 schema、有 trace、有 fallback、有至少一个 eval 指标。

### 7.2 核心流程

```text
读取输入
  -> schema 校验
  -> 执行核心逻辑
  -> 生成结构化输出
  -> 写入 trace
  -> 返回给下一个节点
```

### 7.3 错误处理

每个模块至少处理三类错误：输入为空、LLM 输出无法解析、结果质量不足但还能继续。错误不要直接让系统崩溃，而要返回结构化状态：

```json
{
  "status": "warn",
  "failure_type": "invalid_llm_json",
  "fallback_used": true,
  "next_action": "use_rule_based_fallback"
}
```

### 7.4 Trace 设计

Trace 至少记录：node name、input summary、output summary、latency、fallback_used、关键分数或决策。不要把超长文本全塞 trace，可以存 chunk_id 和摘要。

## 8. 具体实施步骤

1. 在 `app/schemas/` 下定义本模块输入输出 schema。  
2. 在 `app/modules/` 下实现最小规则版，保证稳定。  
3. 如果需要 LLM，加入 JSON schema、Pydantic 校验和 fallback。  
4. 写 LangGraph node，把输入从 state 取出，把输出写回 state。  
5. 把关键决策写入 `state['trace']`。  
6. 准备 5～10 个样例输入做单元测试。  
7. 在 eval report 中加入该模块相关指标或案例。  

## 9. 推荐代码骨架

```python
class ModuleConfig(BaseModel):
    enabled: bool = True
    debug: bool = False

class ModuleResult(BaseModel):
    status: Literal['ok','warn','fail'] = 'ok'
    data: dict
    trace: dict
    next_action: str | None = None

class Module:
    def __init__(self, config: ModuleConfig):
        self.config = config

    def run(self, input_data: dict) -> ModuleResult:
        # 1. validate input
        # 2. execute core logic
        # 3. build trace
        # 4. return result
        return ModuleResult(data={}, trace={'module': 'Grounded Answer Generator', 'status': 'ok'})
```

## 10. 调试方法

调试时不要只看最终答案，要逐层看中间结果：输入是否符合预期、输出是否结构化、是否触发 fallback、trace 是否完整、后续模块是否真的使用了这个模块输出。

## 11. 验收标准

- 可以独立调用。  
- 可以接入 AgentState。  
- 输出通过 schema 校验。  
- 关键决策进入 trace。  
- 有至少 5 个测试样例。  
- 在 eval report 中能体现作用。  

## 12. 常见坑

- 模块职责太大，抢其他模块工作。  
- 只写 prompt，不写 schema。  
- LLM 输出坏了没有 fallback。  
- README 写得很高级，但代码里没有 trace/eval。  
- 一开始设计过重，两周内无法完成。  


### 专属设计

Prompt 约束：只能使用 evidence pack；核心结论必须带 citation_id；证据不足就说明不足；不能编造引用。

```python
class GroundedAnswer(BaseModel):
    answer: str
    used_citations: list[str]
    unsupported_claims: list[str] = []
    confidence: Literal['high','medium','low']
```

生成后先做规则自检：答案里的 citation_id 是否存在于 evidence pack。


## 15. 两周项目优先级

第一周：实现最小可运行版本并接入主图。  
第二周：补充 trace、测试、eval 统计和 README 解释。  
如果时间不够，优先保证它在主流程中稳定发挥作用，而不是追求完整复刻论文或工业平台。
