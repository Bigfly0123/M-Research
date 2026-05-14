from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.llm import get_llm

"""
================================================================================
【学习指南】router.py - 意图识别与动态路由
================================================================================

📚 核心概念:
Router 是整个工作流的"前台接待员",负责判断用户的意图:
- NEW_TOPIC: 要开始一个新的研究课题
- REFINE: 要修改已有的报告

🎯 为什么需要 Router?
1. 提升用户体验: 用户可以直接说"把第一章改详细点",不用重新上传文档
2. 节省资源: Refine 模式跳过耗时的检索和规划环节
3. 支持多轮对话: 基于已有报告进行迭代优化

💡 类比理解:
想象你去图书馆:
- NEW_TOPIC: "我想查一下量子计算的资料" → 图书管理员去书架找新书
- REFINE: "刚才那本书太难了,换本简单的" → 图书管理员在现有基础上调整

🔑 关键函数说明:

1. looks_like_refine(q: str) -> bool:
   - 作用: 基于关键词的规则判断(兜底策略)
   - 逻辑: 检查用户输入中是否包含"修改类"关键词(改、润色、优化、补充等)
   - 场景: 当 LLM 无法正确判断意图时,作为后备方案
   - 设计思想: "LLM + 规则"的双重保障,提高鲁棒性

2. route_query(state: AgentState) -> str:
   - 作用: 分析用户输入,决定工作流从哪个节点开始执行
   - 决策流程:
     Step 1: 检查是否有历史报告 → 没有则直接返回 "planner"
     Step 2: 构造 Prompt 让 LLM 判断(包含用户输入 + 报告片段)
     Step 3: 解析 LLM 输出 → "REFINE" 或 "NEW_TOPIC"
     Step 4: 如果 LLM 输出格式错误 → 启用兜底规则(关键词匹配)
   
   - 典型场景:
     * 首次提问: final_report 为空 → "planner"
     * 基于报告追问: "把技术原理部分写详细点" → LLM 判断 "REFINE" → "refiner"
     * 开启新话题: "帮我查一下量子计算" → LLM 判断 "NEW_TOPIC" → "planner"
     * LLM 抽疯: 输出格式错误 → looks_like_refine() 兜底

🎓 学习要点:
1. 上下文感知: 不是孤立地看用户输入,而是结合历史状态(final_report)做判断
2. 渐进式降级: LLM 判断 → 规则匹配 → 默认策略 (智能 → 可靠 → 保底)
3. Prompt 工程: 提供足够的上下文,明确要求输出格式,用示例引导模型行为
4. 容错设计: .strip().upper() 清理输出,兜底策略保证系统不会崩溃

⚠️ 注意事项:
- report[:50] 只取前50字符,避免 Prompt 过长
- LLM 的温度应该设低一些(接近 0),保证稳定性

🔗 与其他模块的关系:
- graph.py: 调用此函数决定入口点
- planner.py: NEW_TOPIC 的目的地
- refiner.py: REFINE 的目的地
================================================================================
"""

# 使用小模型做路由判断,速度快、成本低(因为这是简单的分类任务)
router_llm = get_llm()


def looks_like_refine(q: str) -> bool:
    """兜底策略:基于关键词的规则判断。检查用户输入中是否包含'修改类'关键词。"""
    q = q.strip()
    refine_triggers = ["改", "润色", "优化", "补充", "扩写", "写详细", "更通俗", "更正式", "重写", "调整", "删", "加", "第", "章", "段", "标题", "格式", "总结", "结论", "引用"]
    return any(t in q for t in refine_triggers)

def route_query(state: AgentState):
    """
    核心函数:意图识别路由器
    
    分析用户输入,决定工作流从哪个节点开始执行。
    
    决策流程:
    1. 检查是否有历史报告 → 没有则直接返回 "planner"
    2. 构造 Prompt 让 LLM 判断(包含用户输入 + 报告片段)
    3. 解析 LLM 输出 → "REFINE" 或 "NEW_TOPIC"
    4. 如果 LLM 输出格式错误 → 启用兜底规则(关键词匹配)
    
    参数:
    - state: 当前的 AgentState,包含 query 和 final_report
    
    返回:
    - str: 下一个节点名称 ("planner" 或 "refiner")
    """
    query = state["query"]
    has_report = bool(state.get("final_report", "").strip())

    print(f"--- [Router] 正在分析意图: '{query}' (已有报告: {has_report}) ---")

    if not has_report:
        return "planner"
    final_report = state["final_report"]
    report = final_report[:50]

    prompt = f"""
    当前系统已经生成了一份研究报告。
    用户的最新输入是: "{query}"。
    用户最近一次生成的报告片段是："{report}"
    
    请判断用户的意图：
    1. "NEW_TOPIC": 用户想要开始一个全新的研究课题（例如："帮我查一下量子计算"）。
    2. "REFINE": 用户想要基于现有的报告进行修改、润色或补充（例如："第一章写详细点"、"改通俗点"）。
    
    只输出 "NEW_TOPIC" 或 "REFINE"。
    """
    
    result = router_llm.invoke([HumanMessage(content=prompt)]).content.strip().upper()
    print(f"--- [Router] LLM 判定结果: {result} ---")
    
    if result == "REFINE":
        return "refiner"  # 去专门的修改节点
    if result == "NEW_TOPIC":
        return "planner"  # 开启新课题
    # 兜底：模型没按要求输出
    print(f"--- [Router][WARN] 非法输出: {result!r}，启用兜底规则 ---")
    return "refiner" if looks_like_refine(query) else "planner"

def test():
    """测试函数:验证 Router 的功能。运行: python -m app.graph.nodes.router"""
    state:AgentState={
        "query":"写详细一点",
        "final_report": "Transformer发展"
    }
    print(route_query(state))

# python -m app.graph.nodes.router
# test()
# print(looks_like_refine("将第一段改的更通俗"))

# 流式输出
# res = router_llm.stream([HumanMessage(content='你是谁')])
# for chunk in res:
#     print(chunk.content, end='', flush=True)
