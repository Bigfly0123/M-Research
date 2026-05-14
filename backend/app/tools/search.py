from tavily import TavilyClient
import os
from dotenv import load_dotenv

"""
================================================================================
【学习指南】search.py - 网络搜索工具
================================================================================

📚 核心概念:
Tavily 是一个专为 AI Agent 设计的搜索引擎 API,提供结构化、干净的搜索结果。
相比传统搜索引擎,Tavily 的优势是:
1. 结果更精准: 自动过滤广告和低质量内容
2. 格式友好: 返回结构化的 JSON,易于解析
3. 为 LLM 优化: 提取核心内容,减少噪音

🎯 为什么需要网络搜索?
1. 补充实时信息: RAG 只能访问上传的文档,无法获取最新信息
2. 扩大知识范围: 当本地文档不足时,从互联网获取补充资料
3. 混合模式: Document + Web Search 结合,提高回答质量

💡 类比理解:
想象你要写一篇综述论文:
- RAG (本地文档): 查阅图书馆的藏书(私有、权威)
- Tavily (网络搜索): 上网查最新资料(实时、广泛)
- 两者结合 = 完整的文献调研

🔑 关键函数说明:

search_tavily(query: str) -> str:
   - 作用: 使用 Tavily API 执行网络搜索
   - 输入: query (搜索关键词)
   - 输出: 拼接后的搜索结果字符串(最多 3 条)
   
   - 工作流程:
     Step 1: 调用 tavily.search() API
             ├─ search_depth="basic": 基础搜索深度(速度快)
             └─ max_results=3: 只取前 3 条结果(节省 Token)
     
     Step 2: 提取 content 字段
             └─ 从每条结果中取出核心内容
     
     Step 3: 拼接成字符串
             └─ 用换行符连接,返回给 Researcher
   
   - 配置说明:
     * TAVILY_API_KEY: 需要在 .env 文件中配置
     * search_depth: "basic"(快速) 或 "advanced"(深入但慢)
     * max_results: 根据实际需求调整,太多会消耗大量 Token

🎓 学习要点:
-----------
1. API 封装思想:
   - 将外部服务封装成简单函数
   - 隐藏实现细节,提供清晰接口
   - 便于替换(可以换成其他搜索引擎)

2. Token 控制:
   - max_results=3: 限制结果数量
   - 只取 content: 不返回 URL、标题等冗余信息
   - 避免上下文窗口爆炸

3. 错误处理:
   - 实际项目中应该加入 try-except
   - 处理 API 限流、网络超时等情况
   - 提供降级方案(如返回空字符串)

4. 搜索策略:
   - basic vs advanced: 根据场景选择
   - 可以加入时间过滤、语言过滤等参数
   - 支持高级搜索语法

⚠️ 注意事项:
-----------
- Tavily 是付费服务,有调用次数限制
- 需要注册账号获取 API Key: https://tavily.com/
- 生产环境需要考虑缓存机制,避免重复搜索
- 敏感话题可能需要加入内容过滤

🔗 与其他模块的关系:
-------------------
- graph/nodes/researcher.py: 在 hybrid 模式下调用此函数
- .env 文件: 存储 TAVILY_API_KEY
- utils/llm.py: 同样需要从 .env 读取 API Key

📊 典型使用场景:
--------------
场景 1: Hybrid 模式 + 文档相关
→ 先用 RAG 检索本地文档
→ 再用 Tavily 补充网络信息
→ Writer 综合两者生成报告

场景 2: Hybrid 模式 + 文档不相关
→ RAG 结果为空或不相关
→ 完全依赖 Tavily 网络搜索
→ 前端显示警告:"本地文档无关,已切换全网搜索"

场景 3: Document Only 模式
→ 不调用 Tavily
→ 仅使用本地文档
→ 如果文档不相关,should_stop=True 提前终止

================================================================================
"""

load_dotenv()

# 初始化 Tavily 客户端
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def search_tavily(query: str):
    """
    使用 Tavily 搜索网络
    
    调用 Tavily API 执行网络搜索,返回最相关的搜索结果。
    
    参数:
    - query: 搜索关键词(通常来自 Planner 生成的 plan)
    
    返回:
    - str: 拼接后的搜索结果(最多 3 条,用换行符分隔)
    
    配置:
    - search_depth="basic": 基础搜索,速度快
    - max_results=3: 只取前 3 条结果,节省 Token
    
    使用示例:
    ```python
    results = search_tavily("AI Agent 发展趋势")
    # 返回: "结果1内容\n结果2内容\n结果3内容"
    ```
    """
    print(f"--- [工具调用] 正在搜索: {query} ---")
    response = tavily.search(query=query, search_depth="basic", max_results=3)
    
    # 提取我们关心的内容（为了节省 Token，只取 content）
    context = [result["content"] for result in response["results"]]
    return "\n".join(context)
