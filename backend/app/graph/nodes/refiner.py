from langchain_core.messages import HumanMessage
from app.graph.state import AgentState
from app.utils.llm import get_llm

"""
================================================================================
【学习指南】refiner.py - 内容精修师
================================================================================

📚 核心概念:
Refiner 是工作流中的"编辑",负责根据用户的修改指令,对已有报告进行局部调整。
与 Planner → Researcher → Writer 的完整流程不同,Refiner 直接修改现有报告,
跳过耗时的检索和规划环节。

🎯 为什么需要 Refiner?
1. 快速响应: 用户说"改通俗点",不需要重新检索和规划
2. 节省资源: 避免重复调用 LLM 和搜索 API
3. 保持连贯: 只修改用户指定的部分,其余内容保持原样
4. 多轮对话: 支持基于报告的连续追问和迭代优化

💡 类比理解:
想象你写完论文后:
- 导师说:"摘要写得太专业了,改得通俗一点"
- 你不需要重新做实验、查文献
- 只需要在现有基础上修改摘要部分

🔑 关键函数说明:

refine_node(state: AgentState) -> Dict:
   - 作用: 根据用户指令修改现有报告
   - 输入: state["query"] (修改指令) + state["final_report"] (原始报告)
   - 输出: {"final_report": str, "review_status": "PASS"}
   
   - 工作流程:
     Step 1: 提取用户修改指令(query)和原始报告(final_report)
     Step 2: 构造 Prompt,包含原始报告和修改指令
     Step 3: 调用 LLM 生成修改后的报告
     Step 4: 返回新报告,并设置 review_status="PASS"(默认通过)
   
   - Prompt 设计要点:
     * 角色设定: "你是一个专业的报告编辑"
     * 任务明确: "根据用户的指令,对原始报告进行修改"
     * 约束条件:
       - 保持原有的 Markdown 结构
       - 只修改用户要求的部分,其余部分尽量保持原汁原味
       - 直接输出修改后的完整报告,不要有任何前言后语
   
   - 典型场景:
     * 场景1: "把第一章改得通俗一点"
       → LLM 只修改第一章,其他章节保持不变
     
     * 场景2: "增加一个案例分析部分"
       → LLM 在报告中插入新的案例章节
     
     * 场景3: "总结成 500 字以内"
       → LLM 压缩报告内容

🎓 学习要点:
1. 局部修改: 不是重新生成,而是在现有基础上调整,提高效率
2. 指令跟随: LLM 需要准确理解用户的修改意图
3. 结构保持: 保持 Markdown 格式和整体结构的一致性
4. 默认通过: Refiner 之后不再审查,直接输出给用户(假设用户自己会判断)

⚠️ 注意事项:
- LLM 可能会过度修改,需要在 Prompt 中强调"只修改用户要求的部分"
- 对于复杂的修改指令,可能需要多次迭代
- 如果修改幅度过大,可能不如重新走完整流程

🔗 与其他模块的关系:
- graph.py: Router 判断为 REFINE 时进入 refiner,完成后直接 END
- router.py: 通过意图识别决定是否进入 refiner
- reviewer.py: Refiner 跳过了 Reviewer,假设用户自己会判断质量
================================================================================
"""

llm = get_llm()

def refine_node(state: AgentState):
    """
    内容精修节点:根据用户指令修改现有报告
    
    对已有报告进行局部调整,跳过耗时的检索和规划环节。
    
    参数:
    - state: 当前的 AgentState,包含 query(修改指令) 和 final_report(原始报告)
    
    返回:
    - {"final_report": str, "review_status": "PASS"}
    
    工作流程:
    1. 提取用户修改指令和原始报告
    2. 构造 Prompt,包含原始报告和修改指令
    3. 调用 LLM 生成修改后的报告
    4. 返回新报告,并设置 review_status="PASS"
    """
    query = state["query"]               # 修改指令，例如 "把第一章改详细点"
    old_report = state.get("final_report", "")
    
    print(f"--- [Refiner] 正在根据指令修改报告: {query} ---")
    
    prompt = f"""
    你是一个专业的报告编辑。
    
    【原始报告】
    {old_report}
    
    【用户修改指令】
    {query}
    
    请根据用户的指令，对原始报告进行修改。
    注意：
    1. 保持原有的 Markdown 结构。
    2. 只修改用户要求的部分，其余部分尽量保持原汁原味。
    3. 直接输出修改后的完整报告，不要有任何前言后语。
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    new_report = response.content
    
    return {
        "final_report": new_report,
        "review_status": "PASS" # 修改后默认通过，直接给用户看
    }
