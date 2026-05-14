import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

"""
================================================================================
【学习指南】llm.py - LLM 模型工厂
================================================================================

📚 核心概念:
这个文件封装了 LLM (大语言模型) 的初始化和配置,提供统一的接口供其他模块调用。

🎯 为什么需要模型工厂?
1. 统一管理: 所有 LLM 配置集中在一处,便于维护
2. 灵活切换: 可以轻松更换模型提供商(OpenAI、DeepSeek、Claude等)
3. 分级使用: 不同任务使用不同模型,平衡成本和性能
4. 环境变量: API Key 不硬编码,保证安全性

💡 类比理解:
想象一个公司的用车制度:
- 普通员工出差 → 经济型轿车(fast 模型,便宜快速)
- CEO 重要会议 → 豪华轿车(smart 模型,昂贵但可靠)
- 统一由行政部门调度(get_llm 函数)

🔑 关键设计思想:

双模型策略:
--------------
IRIS 使用了两种不同配置的 LLM:

1. Fast 模型 (qwen-max):
   - 用途: Planner、Writer、Router 等生成类任务
   - 特点: temperature=0.7,有一定创造力
   - 优势: 速度快、成本低、文本流畅
   - 场景: 生成报告、规划任务、意图识别

2. Smart 模型 (deepseek-r1):
   - 用途: Reviewer、Relevance Grader 等审查类任务
   - 特点: temperature=0,绝对理性
   - 优势: 逻辑严谨、判断准确
   - 场景: 质量审查、相关性判断、JSON 输出

为什么这样设计?
- 生成任务需要创造力和流畅度 → 高 temperature
- 审查任务需要准确性和一致性 → 低 temperature
- 成本优化: 80% 的请求用 fast 模型,20% 用 smart 模型

🔑 关键函数说明:

get_llm(model_type="fast") -> ChatOpenAI:
   - 作用: 根据任务类型返回配置好的 LLM 实例
   - 参数: model_type ("fast" 或 "smart")
   - 返回: LangChain 的 ChatOpenAI 对象
   
   - 配置说明:
     * model: 模型名称(qwen-max / deepseek-r1)
     * temperature: 创造性程度(0-1,0=确定性,1=随机性)
     * base_url: API 地址(支持自定义部署)
     * api_key: 从 .env 读取,不硬编码

🎓 学习要点:
-----------
1. 工厂模式:
   - 隐藏对象创建细节
   - 调用方不需要知道具体配置
   - 便于扩展新模型类型

2. Temperature 调优:
   - 0.0: 完全确定性,适合分类、审查
   - 0.3-0.5: 轻度创造性,适合代码生成
   - 0.7-0.9: 中度创造性,适合写作、创意
   - 1.0+: 高度创造性,适合头脑风暴

3. 环境变量管理:
   - .env 文件存储敏感信息
   - load_dotenv() 自动加载
   - os.getenv() 安全读取
   - 永远不要将 .env 提交到 Git

4. LangChain 集成:
   - ChatOpenAI 是 LangChain 的标准接口
   - 支持 stream、invoke、batch 等方法
   - 可以无缝切换到其他提供商

⚠️ 注意事项:
-----------
- OPENAI_API_BASE 可以是 OpenAI 官方,也可以是兼容 API(如 DeepSeek)
- 不同模型的 token 价格差异很大,注意成本控制
- production 环境应该加入限流和配额管理
- 可以考虑缓存常用响应,减少 API 调用

🔗 与其他模块的关系:
-------------------
- graph/nodes/*.py: 各个节点调用 get_llm() 获取 LLM 实例
- rag/engine.py: Embedding 模型也在这里配置(虽然不在本文件)
- .env 文件: 存储 OPENAI_API_KEY 和 OPENAI_API_BASE

📊 典型使用模式:
--------------
# Planner 节点(需要创造力)
llm = get_llm(model_type="fast")
response = llm.invoke(prompt)

# Reviewer 节点(需要准确性)
llm = get_llm(model_type="smart")
response = llm.invoke(prompt)

# Router 节点(简单分类,用小模型)
router_llm = get_llm()  # 默认 fast

🚀 扩展方向:
-----------
1. 加入更多模型类型:
   - "embedding": 专门用于向量化的模型
   - "coder": 专门用于代码生成的模型

2. 动态选择:
   - 根据问题复杂度自动选择模型
   - 简单问题用 fast,复杂问题用 smart

3. 降级策略:
   - API 失败时自动切换到备用模型
   - 限流时使用本地小模型

4. 成本监控:
   - 记录每次调用的 token 消耗
   - 统计各模型的总花费

================================================================================
"""

# 加载 .env 环境变量
load_dotenv()

def get_llm(model_type="fast"):
    """
    LLM 模型工厂函数
    
    根据任务类型返回配置好的 LLM 实例。
    
    参数:
    - model_type: 模型类型
      * "fast": 快速模型,用于生成类任务(Planner, Writer)
      * "smart": 聪明模型,用于审查类任务(Reviewer)
    
    返回:
    - ChatOpenAI: LangChain 的聊天模型实例
    
    配置说明:
    - Fast 模型: qwen-max, temperature=0.7 (有创造力)
    - Smart 模型: deepseek-r1, temperature=0 (绝对理性)
    
    使用示例:
    ```python
    # 生成报告
    llm = get_llm("fast")
    report = llm.invoke(prompt)
    
    # 审查报告
    llm = get_llm("smart")
    review = llm.invoke(prompt)
    ```
    """
    
    # --- 配置 A: 快速模型 (DeepSeek-V3 / GPT-4o-mini) ---
    # 用于：Planner, Writer (需要速度和流利度)
    if model_type == "fast":
        return ChatOpenAI(
            model="qwen-max", 
            temperature=0.7, # 稍微有点创造力
            base_url=os.getenv("OPENAI_API_BASE"), 
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    # --- 配置 B: 聪明模型 (DeepSeek-R1 / GPT-4o / Claude-3.5) ---
    # 用于：Reviewer (需要严谨逻辑)
    elif model_type == "smart":
        return ChatOpenAI(
            # 建议用 DeepSeek-R1 (推理能力强) 或 GPT-4o
            model="deepseek-r1",
            temperature=0,   # 绝对理性，不要创造力
            base_url=os.getenv("OPENAI_API_BASE"), 
            api_key=os.getenv("OPENAI_API_KEY")
        )
