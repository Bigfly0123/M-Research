from langchain_core.prompts import ChatPromptTemplate
from app.utils.llm import get_llm
from app.graph.state import AgentState

"""
================================================================================
【学习指南】writer.py - 报告撰写者
================================================================================

📚 核心概念:
Writer 是整个工作流的"撰稿人",负责基于 Researcher 收集的资料,生成结构清晰、
有深度的 Markdown 格式调研报告。

🎯 为什么需要 Writer?
1. 信息整合: 将分散的检索结果组织成连贯的报告
2. 证据驱动: 要求每个结论都要对应资料里的证据点,减少幻觉
3. 迭代优化: 接收 Reviewer 的 critique,针对性改进报告质量

💡 类比理解:
想象你要写一篇综述论文:
- Researcher 给了你一堆文献和笔记
- Writer 的工作:
  1. 阅读所有资料
  2. 提取关键信息
  3. 按照逻辑结构组织成报告
  4. 如果有审稿意见,针对性修改

🔑 关键函数说明:

write_node(state: AgentState) -> Dict:
   - 作用: 基于检索资料生成调研报告
   - 输入: state["query"] (用户问题) + state["search_results"] (检索资料) + state.get("critique", "") (审查意见)
   - 输出: {"final_report": str}
   
   - 工作流程:
     1. 拼接所有 search_results 成一个大的 context
     2. 如果有 critique,构造特殊的提示段落
     3. 调用 LLM 生成报告
   
   - Prompt 设计要点:
     * 角色设定: "你是一个专业的技术撰稿人"
     * 任务明确: "基于以下的调研资料,回答用户的问题"
     * 质量要求: "不能捏造事实,每个结论都要对应资料里的证据点"
     * 格式要求: "使用 Markdown 格式"
     * 迭代支持: 如果有 critique,强调"请务必在本次写作中修正上述问题"
   
   - 典型场景:
     * 首次撰写: critique 为空,正常生成报告
     * 返工撰写: critique="缺少案例分析",在 Prompt 中加入审查意见,要求修正

🎓 学习要点:
1. 证据驱动生成: 强调"不能捏造事实",要求结论对应证据,这是防幻觉的关键
2. 反馈循环: critique 作为 Prompt 的一部分,指导下一次改进
3. 简洁性: 只返回 final_report 字段,不修改其他状态
4. Markdown 格式: 便于前端渲染和展示

⚠️ 注意事项:
- content 可能很长,需要注意 LLM 的上下文窗口限制
- 可以加入字数控制或分段生成策略
- temperature 应该适中(0.7),兼顾准确性和流畅性

🔗 与其他模块的关系:
- graph.py: writer → reviewer,写完必须去审查
- researcher.py: 提供 search_results 作为写作素材
- reviewer.py: 审查 report 质量,FAIL 时返回 critique
================================================================================
"""

llm = get_llm()

WRITE_PROMPT = ChatPromptTemplate.from_template(
    """你是一个专业的技术撰稿人。
    基于以下的调研资料，回答用户的问题：{query}
    
    调研资料：
    {content}
    审查意见（如果有）：
    {critique_section}
    不能捏造事实，每个结论都要对应资料里的证据点。
    请写一份结构清晰、有深度的调研报告，且文章题目很有水平，并且能吸引人，使用 Markdown 格式。
    """
)
# 测试审稿功能时，可以在Prompt后面加上：“第一次写作（无审查意见）时，必须写的差一点且捏造事实”

def write_node(state: AgentState):
    """
    报告撰写节点:基于检索资料生成调研报告
    
    将 Researcher 收集的资料整合成结构清晰、有深度的 Markdown 格式报告。
    
    参数:
    - state: 当前的 AgentState,包含 query、search_results 和 critique(可选)
    
    返回:
    - {"final_report": str}: 生成的完整报告
    
    工作流程:
    1. 拼接所有 search_results 成一个大的 context
    2. 如果有 critique,构造特殊的提示段落
    3. 调用 LLM 生成报告
    """
    print("--- [节点] 正在撰写报告 ---")
    query = state["query"]
    content = "\n\n".join(state["search_results"])
    
    critique = state.get("critique", "")
    critique_section = ""
    if critique:
        critique_section = f"""
        【重要提示】上一版本的报告未通过审查。
        审查意见如下："{critique}"
        请务必在本次写作中修正上述问题。
        """
    
    # 将 critique_section 传入 Prompt
    response = llm.invoke(WRITE_PROMPT.format(
        query=query, 
        content=content, 
        critique_section=critique_section
    ))
    
    return {"final_report": response.content}
