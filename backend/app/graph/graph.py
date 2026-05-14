from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.graph.nodes.planner import plan_node
from app.graph.nodes.researcher import research_node
from app.graph.nodes.writer import write_node
from app.graph.nodes.reviewer import review_node 
import json
from app.graph.nodes.router import route_query
from app.graph.nodes.refiner import refine_node

"""
================================================================================
【学习指南】graph.py - LangGraph 工作流编排核心
================================================================================

📚 核心概念:
这个文件是整个 IRIS 系统的"指挥中心",定义了:
1. 有哪些节点(Planner, Researcher, Writer, Reviewer, Refiner)
2. 节点之间如何连接(边/Edge)
3. 在什么条件下走哪条路径(条件边/Conditional Edge)

🎯 LangGraph vs 传统链式调用:
传统 RAG: Input → Retrieve → Generate → Output (线性,不可控)
LangGraph: 有向图结构,支持分支、循环、条件跳转

💡 类比理解:
想象一个工厂流水线:
- 每个节点是一个工作站
- 边是传送带
- 条件边是分叉路口(根据产品质量决定去哪)
- State 是在产品上贴的标签(记录加工进度)

🔑 关键函数说明:

1. route_after_research(state):
   - 作用: Researcher 之后的分流决策
   - 逻辑: 如果 should_stop=True → END,否则 → writer
   - 场景: Document Only 模式下文档不相关时提前终止,避免编造答案
   - 这是"防幻觉熔断机制"的关键实现

2. should_continue(state):
   - 作用: Reviewer 审查后的决策(核心循环控制)
   - 逻辑: 先检查重试次数(revision_number >= 3 → END)
           再检查审查结果(FAIL → planner, PASS → END)
   - 场景: 报告质量不合格时回到 planner 重新规划,带着 critique 作为改进方向
   - 这是 Agentic Workflow 的核心价值:"生成-审查-修正"循环实现自我优化

3. create_graph(memory=None):
   - 作用: 创建并编译 LangGraph 工作流
   - 步骤:
     Step 1: workflow = StateGraph(AgentState)  # 创建工作流骨架
     Step 2: workflow.add_node(...)  # 注册所有节点
     Step 3: workflow.set_conditional_entry_point(route_query, ...)  # 设置入口点
     Step 4: workflow.add_edge(...)  # 添加固定边(确定性流转)
     Step 5: workflow.add_conditional_edges(...)  # 添加条件边(选择性流转)
     Step 6: app = workflow.compile(checkpointer=memory)  # 编译成可执行应用
   
   - 完整工作流图:
     START → [route_query] → NEW_TOPIC → planner → researcher
                               REFINE → refiner → END
     
     researcher → [route_after_research] → should_stop → END
                                         → normal → writer
     
     writer → reviewer → [should_continue] → FAIL → planner (循环)
                                             → PASS → END

🎓 学习要点:
1. 声明式编程: 不是写一堆 if-else,而是声明节点和边的关系,LangGraph 负责执行调度
2. 可视化友好: 可以用 app.get_graph().draw_mermaid_png() 生成流程图
3. 灵活性: 可以轻松添加新节点,动态调整路由逻辑
4. 生产级特性: Checkpointing 支持持久化、断点续跑、多轮对话记忆

🔗 与其他模块的关系:
- state.py: 定义工作流的状态结构
- nodes/*.py: 提供各个节点的具体实现
- routes.py: 调用 create_graph() 创建应用并执行
================================================================================
"""

def route_after_research(state: AgentState):
    """Researcher 结束后的交通指挥员。检查 state['should_stop'] 是否为 True。"""

    if state.get("should_stop", False):
        print("--- [路由] 检测到停止信号 (should_stop=True) -> 🛑 提前结束任务 ---")
        return END  
    else:
        return "writer"

def should_continue(state: AgentState):
    """
    决定下一步去哪里的函数。
    返回下一个节点的名称 (字符串) 或 END。
    """
 
    current_revision = state.get("revision_number", 0)
    if current_revision >= 3:
        print("--- [路由] 已达到最大重试次数，强制结束 ---")
        return END

    review_status = state.get("review_status", "PASS")
    critique = state.get("critique", "")
    
    if review_status == "FAIL":
        print(f"--- [路由] 审查未通过 (意见: {critique}) -> 返回规划节点 ---")
        return "planner" 
    else:
        print("--- [路由] 审查通过 -> 结束 ---")
        return END

def create_graph(memory=None):
    """
    工厂函数:创建并编译 LangGraph 工作流
    
    构建步骤:
    1. 创建状态图: workflow = StateGraph(AgentState)
    2. 注册节点: workflow.add_node("节点名", 节点函数)
    3. 设置入口点: workflow.set_conditional_entry_point(route_query, {...})
    4. 添加固定边: workflow.add_edge("源节点", "目标节点")
    5. 添加条件边: workflow.add_conditional_edges("源节点", 路由函数, {...})
    6. 编译: app = workflow.compile(checkpointer=memory)
    
    参数:
    - memory: AsyncSqliteSaver 实例,用于持久化状态,支持断点续跑和多轮对话
    
    返回:
    - app: 编译后的 LangGraph 应用,可调用 app.invoke() 或 app.astream()
    """

    workflow = StateGraph(AgentState)

    workflow.add_node("planner", plan_node)
    workflow.add_node("researcher", research_node)
    workflow.add_node("writer", write_node)
    workflow.add_node("reviewer", review_node)
    workflow.add_node("refiner", refine_node)

    # START -> planner -> researcher -> writer -> reviewer -> END/planner
    workflow.set_conditional_entry_point(
        route_query,
        {
            "planner": "planner",
            "refiner": "refiner"
        }
    )
    workflow.add_edge("planner", "researcher")
    workflow.add_conditional_edges(
        "researcher",
        route_after_research,
        {
            "writer": "writer",
            END: END
        }
    )
    workflow.add_edge("writer", "reviewer")

    workflow.add_conditional_edges(
        "reviewer",
        should_continue,
        {
            "planner": "planner",
            END: END
        }
    )
    workflow.add_edge("refiner", END)


    app = workflow.compile(checkpointer=memory)
    return app
