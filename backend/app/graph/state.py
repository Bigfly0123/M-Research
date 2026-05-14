from typing import TypedDict, List, Annotated
import operator

"""
================================================================================
【学习指南】AgentState - IRIS 系统的共享状态设计
================================================================================

📚 核心概念:
在 LangGraph 构建的 Agent 工作流中,多个节点(Planner、Researcher、Writer等)需要
共享数据和传递信息。AgentState 就是这个"共享文件夹",所有节点都可以从中读取数据
或写入新的数据。

🎯 为什么需要 TypedDict?
1. 类型安全: IDE 可以提供代码补全和类型检查
2. 结构清晰: 一眼就能看出系统维护了哪些状态
3. 文档作用: 新开发者能快速理解数据流转

💡 类比理解:
想象一个团队协作写报告的场景:
- Planner 是项目经理,制定计划(plan)
- Researcher 是研究员,收集资料(search_results)
- Writer 是撰稿人,撰写报告(final_report)
- Reviewer 是审核员,给出意见(critique)

所有人都在这张"共享表格"(AgentState)上工作,每个人完成自己的任务后,
更新对应的字段,下一个人就能看到前面的成果。

🔑 关键字段说明:
- query: 用户原始问题,在整个流程中保持不变
- plan: Planner 生成的搜索子问题列表,Researcher 会逐个执行
- search_results: Researcher 收集的所有资料(本地文档 + 网络搜索)
- final_report: Writer 生成的完整 Markdown 报告
- critique: Reviewer 给出的审查意见,FAIL 时包含改进建议
- revision_number: 当前是第几次修改/重试,防止无限循环(最多3次)
- review_status: 审查结果,"PASS" 或 "FAIL"
- search_mode: 搜索模式,"document"(仅本地) 或 "hybrid"(混合)
- should_stop: 紧急停止信号,文档完全不相关时触发

🎓 设计亮点:
1. 增量更新机制: 节点函数返回"部分更新",LangGraph 自动合并
2. 可追溯性: 保留完整中间过程,便于调试和 SSE 展示
3. 防幻觉机制: should_stop 让系统知道什么时候不应该回答
4. 反馈循环: critique 实现自我修正,回到 planner 重新规划

🔗 与其他模块的关系:
- graph.py: 定义节点如何读写这些状态
- nodes/*.py: 各个节点函数接收 AgentState,返回部分字段的更新
- routes.py: API 层初始化 state 并接收最终结果
================================================================================
"""

class AgentState(TypedDict):
    """Agent 的状态定义 - 整个工作流的"中央数据库"""
    
    query: str                # 用户原始问题
    plan: List[str]           # 规划的搜索步骤
    search_results: List[str] # 搜索到的具体内容
    final_report: str         # 最终生成的报告
    critique: str             # 审查意见
    revision_number: int      # 当前修改到了第几版 (防止死循环)
    review_status: str        # "PASS" 或 "FAIL"
    search_mode: str          # 取值: "document" (只查文档) 或 "hybrid" (混合搜索)
    should_stop: bool         # 控制位
