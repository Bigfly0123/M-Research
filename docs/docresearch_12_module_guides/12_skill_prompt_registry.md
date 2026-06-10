# 12｜Skill Prompt Registry 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Skill Prompt Registry 管理项目中的 prompt、rubric、schema、examples，避免提示词散落在代码里。它让项目更像工程系统，也方便做版本控制和 eval 复现。

## 2. 必须理解的知识点
- **Prompt String**：一段写死在代码里的提示词。
- **Skill Module**：包含 instructions、schema、rubric、examples 的能力包。
- **Rubric**：Judge/Evaluator 的评分规则。
- **Versioning**：每个 skill 有版本，trace 中记录版本。

## 3. 技术参考
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents)
- [MCP Tools Spec](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

## 4. 目录结构
```text
skills/
├── context_planner/
│   ├── instructions.md
│   ├── schema.json
│   └── examples.json
├── retrieval_evaluator/
│   ├── instructions.md
│   ├── rubric.yaml
│   └── schema.json
├── grounded_answer_generator/
│   ├── instructions.md
│   └── schema.json
├── self_reflection_judge/
│   ├── instructions.md
│   ├── rubric.yaml
│   └── failure_types.yaml
├── citation_guardrails/
│   ├── instructions.md
│   └── rubric.yaml
└── eval_report_writer/
    ├── instructions.md
    └── template.md
```

## 5. Skill Metadata
```yaml
name: self_reflection_judge
version: 0.1.0
description: Evaluate answer relevance, citation support, faithfulness and context sufficiency.
inputs: [question, context_pack, answer]
outputs: [pass, scores, failure_type, repair_action]
```

## 6. 实施步骤
1. 创建 skills 目录。
2. 先迁移 5 个核心 prompt：planner、retrieval_evaluator、answer_generator、judge、eval_report_writer。
3. 实现 SkillRegistry loader。
4. 业务节点通过 registry 获取 prompt。
5. trace 记录 skill_name 和 version。

## 7. 伪代码
```python
class SkillRegistry:
    def __init__(self, root='skills'):
        self.skills = load_all_skills(root)

    def render(self, skill_name, variables):
        skill = self.skills[skill_name]
        return render_template(skill.instructions, variables)
```

## 8. 验收标准
- prompt 不散落在代码里。
- Judge/Evaluator 有 rubric。
- 每个 skill 有 version。
- trace 记录 skill version。
- 修改 prompt 不需要改业务代码。

## 9. 常见坑
- 做成复杂 prompt 管理平台，拖慢进度。
- 只有 instructions，没有 schema。
- skill 命名混乱。
- 不记录版本，eval 不可复现。
