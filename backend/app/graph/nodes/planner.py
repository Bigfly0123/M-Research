from langchain_core.prompts import ChatPromptTemplate
from app.utils.llm import get_llm
from app.graph.state import AgentState

"""
================================================================================
【学习指南】planner.py - 任务规划器
================================================================================

📚 核心概念:
Planner 是整个工作流的"项目经理",负责将用户的复杂问题拆解成多个可执行的搜索子问题。

🎯 为什么需要 Planner?
1. 分解复杂度: 大问题 → 小问题,逐个击破
2. 指导检索: Researcher 会根据 plan 列表逐个执行搜索
3. 支持迭代: Reviewer 的 critique 会指导下一次规划,针对性补充缺失信息

💡 类比理解:
想象你要写一篇论文:
- 用户问题: "AI Agent 的发展趋势"
- Planner 拆解: 
  1. "AI Agent 核心技术架构"
  2. "2026年 Agent 发展趋势"
  3. "主流 Agent 框架对比"
- Researcher 根据这 3 个子问题分别搜索资料

🔑 关键函数说明:

plan_node(state: AgentState) -> Dict:
   - 作用: 生成搜索子问题列表
   - 输入: state["query"] (用户问题) + state.get("critique", "") (审查意见)
   - 输出: {"plan": ["子问题1", "子问题2", ...]}
   
   - 工作流程:
     1. 构造 Prompt,包含用户问题和上一次的审查意见(如果有)
     2. 调用 LLM 生成 3-5 个搜索关键词/子问题
     3. 用逗号分隔解析成列表
   
   - 典型场景:
     * 首次规划: critique 为空,基于原始问题生成计划
     * 返工规划: critique="缺少案例分析",针对这个意见生成新的搜索方向
   
   - Prompt 设计要点:
     * 明确要求: "只返回关键词,用逗号分隔,不要有其他废话"
     * 提供示例: "例如：子问题1, 子问题2, 子问题3"
     * 强调针对性: "如果存在审查意见,请务必针对意见中提到的缺失信息生成关键词"

🎓 学习要点:
1. 任务分解思想: 将复杂问题拆成可执行的小任务,提高检索质量
2. 反馈驱动: critique 作为下一轮规划的输入,实现针对性改进
3. Prompt 工程: 明确格式要求,提供示例,减少后处理难度
4. 简洁性: 只返回必要的 plan 字段,不修改其他状态

⚠️ 注意事项:
- LLM 可能不按逗号分隔,实际项目中需要更健壮的解析逻辑
- plan 的数量影响 Researcher 的工作量,太多会导致超时或 Token 超限
- 可以限制 plan 的最大数量(如最多 5 个)

🔗 与其他模块的关系:
- graph.py: planner → researcher,规划完必须去检索
- researcher.py: 遍历 plan 列表,逐个执行搜索
- reviewer.py: FAIL 时的 critique 会传回 planner,指导下一次规划
================================================================================
"""

llm = get_llm()


PLAN_PROMPT = ChatPromptTemplate.from_template(
    """你是一个专业的调研助手。
    针对用户的问题：{query}
    请生成 3-5 个简短的搜索子问题，用于在 Google 上查找相关信息。
    已有审查意见（如果有）：{critique}
    如果存在审查意见，请务必针对意见中提到的缺失信息生成关键词。
    只返回关键词，用逗号分隔，不要有其他废话。
    例如：子问题1, 子问题2, 子问题3
    """
)

def plan_node(state: AgentState):
    """
    任务规划节点:生成搜索子问题列表
    
    将用户的复杂问题拆解成多个可执行的搜索子问题,指导 Researcher 进行检索。
    
    参数:
    - state: 当前的 AgentState,包含 query 和 critique(可选)
    
    返回:
    - {"plan": List[str]}: 搜索子问题列表
    
    工作流程:
    1. 从 state 中提取 query 和 critique
    2. 调用 LLM 生成 3-5 个搜索关键词
    3. 用逗号分隔解析成列表
    """
    print("--- [节点] 正在规划搜索路径 ---")
    query = state["query"]
    critique = state.get("critique", "") 
    response = llm.invoke(PLAN_PROMPT.format(query=query, critique=critique))
    plans = [p.strip() for p in response.content.split(",")]
    return {"plan": plans}

def test():
    """测试函数:验证 Planner 的功能。运行: python -m app.graph.nodes.planner"""
    state:AgentState={
        "query":"Transformer发展现状"
    }
    print(plan_node(state))

# python -m app.graph.nodes.planner
# test()
