from langchain_core.messages import HumanMessage
from app.tools.search import search_tavily
from app.graph.state import AgentState
from app.rag.engine import get_retriever
from app.utils.llm import get_llm

"""
================================================================================
【学习指南】researcher.py - 深度研究员
================================================================================

📚 核心概念:
Researcher 是整个工作流的"信息收集员",负责根据 Planner 生成的计划,从本地文档库
和互联网上收集相关资料。

🎯 为什么需要 Researcher?
1. 多源检索: 支持本地文档(RAG)和网络搜索(Tavily)两种模式
2. 相关性审计: 在返回结果前检查文档是否与问题相关,避免噪音
3. 动态策略: 根据 search_mode 和文档相关性自动调整检索策略

💡 类比理解:
想象你要写一篇综述论文:
- Planner 给了你 3 个研究方向
- Researcher 的工作:
  1. 先去图书馆(本地文档库)查资料
  2. 如果图书馆的书不相关,去网上(Tavily)搜索
  3. 把找到的资料整理好交给 Writer

🔑 关键函数说明:

research_node(state: AgentState) -> Dict:
   - 作用: 执行多源检索,收集相关资料
   - 输入: state["query"] (用户问题) + state["plan"] (搜索计划) + state["search_mode"] (搜索模式)
   - 输出: {"search_results": List[str]} 或 {"search_results": [...], "should_stop": True}
   
   - 工作流程:
     Step 1: 尝试从本地知识库检索(RAG)
             ├─ 调用 get_retriever() 获取检索器
             ├─ 执行向量检索 + Rerank
             └─ 进行相关性审计(Relevance Grader)
     
     Step 2: 根据 search_mode 决定后续策略
             ├─ document 模式:
             │   ├─ 文档相关 → 仅使用文档资料
             │   └─ 文档不相关 → should_stop=True,提前终止(防幻觉)
             │
             └─ hybrid 模式:
                 ├─ 文档相关 → 混合模式(Doc + Web)
                 └─ 文档不相关 → 降级为纯网络搜索(Auto-Web)
     
     Step 3: 执行网络搜索(如果需要)
             └─ 遍历 plan 列表,逐个调用 Tavily API
   
   - 相关性审计(Relevance Grader):
     * 作用: 判断检索到的文档是否与问题相关
     * Prompt: "这些文档片段是否包含回答用户问题所需的信息?"
     * 输出: "YES" 或 "NO"
     * 意义: 防止无关文档干扰生成质量
   
   - 典型场景:
     * 场景1: Document Only + 文档相关
       → 仅使用本地文档,不调用网络搜索
     
     * 场景2: Document Only + 文档不相关
       → should_stop=True,返回警告信息,提前终止
     
     * 场景3: Hybrid + 文档相关
       → 混合模式,本地文档 + 网络搜索
     
     * 场景4: Hybrid + 文档不相关
       → 自动降级为纯网络搜索,前端显示警告弹窗

🎓 学习要点:
1. 多源融合: 结合本地知识库和网络搜索,提高信息覆盖率
2. 质量控制: Relevance Grader 过滤无关文档,提升检索精度
3. 动态路由: 根据模式和文档相关性自动调整策略,灵活应对不同场景
4. 防幻觉机制: should_stop 让系统知道什么时候不应该强行回答
5. 用户体验: 通过警告信息告知用户文档不相关,透明化处理

⚠️ 注意事项:
- Tavily API 有调用限制,plan 数量不宜过多(建议 3-5 个)
- 相关性审计依赖 LLM 判断,可能误判,实际项目可以加入阈值控制
- raw_context[:2000] 截取部分文档,避免 Prompt 过长

🔗 与其他模块的关系:
- graph.py: researcher → [route_after_research] → writer 或 END
- rag/engine.py: 提供 get_retriever() 实现本地文档检索
- tools/search.py: 提供 search_tavily() 实现网络搜索
- reviewer.py: 如果报告质量不合格,critique 会传回 planner,重新生成 plan
================================================================================
"""

llm = get_llm(model_type="smart")

def research_node(state: AgentState):
    """
    深度研究节点:执行多源检索,收集相关资料
    
    根据 Planner 生成的计划,从本地文档库和互联网上收集相关资料。
    
    参数:
    - state: 当前的 AgentState,包含 query、plan 和 search_mode
    
    返回:
    - {"search_results": List[str]}: 收集到的资料列表
    - 或 {"search_results": [...], "should_stop": True}: 提前终止信号
    
    工作流程:
    1. 尝试从本地知识库检索(RAG)
    2. 进行相关性审计(Relevance Grader)
    3. 根据 search_mode 决定后续策略
    4. 执行网络搜索(如果需要)
    """

    mode = state.get("search_mode", "hybrid")
    query = state["query"]
    plans = state["plan"]
    results = []

    print(f"--- [Researcher] 开始搜索 | 模式: {mode} ---")
    
    retriever = get_retriever()
    rag_content = ""
    is_doc_relevant = False
    
    if retriever:
        print("--- [RAG] 正在检索本地知识库... ---")
        try:
            docs = retriever.invoke(query)
            if docs:
                raw_context = "\n\n".join([f"[文档片段]: {doc.page_content}" for doc in docs])
                print("--- [RAG] 正在进行文档相关性审计... ---")
                grader_prompt = f"""
                你是一个严格的文档相关性评估员。
                
                用户问题: {query}
                检索到的文档片段: 
                {raw_context[:2000]} (截取部分)
                
                请判断：这些文档片段是否包含回答用户问题所需的信息？
                - 如果文档完全不相关（例如问'吃什么'但文档是'深度学习'），请回答 "NO"。
                - 如果文档相关或部分相关，请回答 "YES"。
                
                只输出 "YES" 或 "NO"，不要输出其他内容。
                """
                grade = llm.invoke([HumanMessage(content=grader_prompt)]).content.strip().upper()
                if "YES" in grade:
                    is_doc_relevant = True
                    rag_content = "\n\n".join([f"[文档片段]: {doc.page_content}" for doc in docs])
                    results.append(f"### 📂 本地文档资料 (已核实相关)\n{rag_content}\n")
                    print("--- [RAG] ✅ 文档通过相关性审计 ---")
                else:
                    print(f"--- [RAG] ⚠️ 警告：文档内容与问题 '{query}' 不相关，已自动忽略 ---")
                    results.append(f"[系统提示]: 检索了本地文档，但发现内容与问题不相关，已自动忽略。")
            else:
                print("--- [RAG] 未找到相关内容 ---")
        except Exception as e:
            print(f"--- [RAG] 检索出错: {e} ---")
    else:
        print("--- [RAG] 知识库为空，跳过 ---")
    
    if mode == "document":
        if is_doc_relevant:
            print("--- [策略] 文档相关，按计划仅使用文档 ---")
        else:
            print("--- [策略] 文档不相关，但这又是 Document Only 模式 ---")
            print("[WARNING] 文档内容与问题不匹配，无法生成有效回答") 
            results.append("【严重警告】：用户选择了 Document Only 模式，但上传的文档与问题完全无关。请直接在报告中诚实地告诉用户：“您上传的文档中没有关于此问题的说明”，不要编造答案。")
            return {
                "search_results": results,
                "should_stop": True 
            }


    else: 
        should_web_search = True
        
        if is_doc_relevant:
            print("--- [策略] 文档相关，启用混合增强模式 (Doc + Web) ---")
        else:
            print("--- [策略] 文档不相关，自动切换为全网搜索模式 (Auto-Web) ---")
            print("[WARNING] 本地文档与问题无关，系统已自动切换为全网搜索") # 触发前端弹窗

        if should_web_search:
            print("--- [Web] 正在执行互联网搜索... ---")
            for q in plans:
                try:
                    content = search_tavily(q)
                    results.append(f"### 🌐 网络搜索结果 ({q})\n{content}\n")
                except Exception as e:
                    print(f"--- [Web] 搜索 {q} 失败: {e} ---")
            
    return {"search_results": results}

# 测试
# def test():
#     state:AgentState = {
#         'query':'Transformer',
#         'plan':['Transformer发展历程','Transformer原理'],
#         'search_mode':'hybird'
#     }
#     res = research_node(state)
#     print(res)
# test()
