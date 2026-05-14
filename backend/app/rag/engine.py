import os
import shutil
import traceback
import time
from typing import Any, List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_core import vectorstores
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

"""
================================================================================
【学习指南】engine.py - RAG 检索引擎核心
================================================================================

📚 核心概念:
RAG (Retrieval-Augmented Generation) 检索增强生成,是整个 IRIS 系统的"知识库"。
它负责将用户上传的 PDF 文档处理成向量索引,并提供高效的检索接口。

🎯 RAG 的核心价值:
1. 突破 LLM 知识限制: 让模型能够访问最新的、私有的领域知识
2. 减少幻觉: 基于真实文档生成答案,而不是凭空编造
3. 可追溯性: 每个答案都可以追溯到具体的文档片段

💡 类比理解:
想象你要参加一场开卷考试:
- 传统 LLM: 靠记忆答题(可能记错或过时)
- RAG: 可以翻阅教材和笔记(准确、可查证)

🔑 RAG 完整流程:
--------------

Step 1: 文档加载 (Document Loading)
----------------------------------
使用 PyPDFLoader 读取 PDF 文件
↓
原始 PDF → 文本内容

Step 2: 文本切分 (Text Splitting)
--------------------------------
使用 RecursiveCharacterTextSplitter 将长文档切成小块
↓
长文档 → 多个 chunk (chunk_size=500, overlap=50)

为什么需要切分?
- LLM 上下文窗口有限
- 小 chunk 更精准,便于检索
- overlap 保证上下文连贯性

Step 3: 向量化 (Embedding)
-------------------------
使用 Embedding 模型将文本转成向量
↓
文本 chunk → 向量 (768维或更高)

常用 Embedding 模型:
- DashScopeEmbeddings (阿里云,本项目使用)
- HuggingFaceEmbeddings (本地部署)
- OpenAI Embeddings (付费 API)

Step 4: 向量存储 (Vector Storage)
--------------------------------
使用 Chroma 向量数据库存储向量索引
↓
向量 + 元数据 → Chroma DB (持久化到磁盘)

Step 5: 检索 (Retrieval)
-----------------------
用户提问 → 向量化 → 相似度搜索 → 返回相关 chunk

Step 6: 重排序 (Reranking) ⭐ 关键优化
-------------------------------------
两阶段检索:
1. 向量召回: 快速找出 top 20 候选 (fetch_k=20)
2. CrossEncoder 精排: 对 query-doc pair 精确打分
3. 返回 top 5 (top_k=5)

为什么需要 Rerank?
- 向量相似度是粗排,可能召回不相关内容
- CrossEncoder 考虑 query 和 doc 的交互,更准确
- 牺牲一点速度,换取显著提升的精度

🔑 关键组件说明:

1. RerankRetriever 类:
   - 继承自 BaseRetriever,实现自定义检索器
   - 核心方法: _get_relevant_documents(query)
   - 实现两阶段检索: 向量召回 + CrossEncoder 精排
   
2. get_reranker() 函数:
   - 单例模式,避免重复加载模型(节省内存)
   - 懒加载,第一次调用时才初始化
   - 容错处理: 检查 sentence-transformers 是否安装

3. process_documents(file_paths) 函数:
   - 完整的文档处理流水线: 加载 → 切分 → 向量化 → 存储
   - 批量处理多个 PDF 文件
   - 性能监控: 记录 embedding 和写入耗时
   - 错误日志: 失败时写入 upload_error.log

4. get_retriever() 函数:
   - Agent 调用的统一接口
   - 检查数据库是否存在
   - 返回配置好的 RerankRetriever 实例

5. reset_knowledge_base() 函数:
   - 清空知识库,用于重新上传文档
   - Windows 兼容: 不删除文件夹,只清空 collection
   - 避免文件占用导致的删除失败

🎓 学习要点:
-----------
1. 两阶段检索思想:
   - 第一阶段: 快速粗排(向量相似度)
   - 第二阶段: 精确精排(CrossEncoder)
   - 平衡速度和精度

2. Chunk 策略:
   - chunk_size=500: 较小的粒度,提高检索精度
   - chunk_overlap=50: 保持上下文连贯
   - 可根据文档类型调整(代码文档可以更小,论文可以更大)

3. Embedding 选择:
   - DashScope: 中文效果好,需要 API Key
   - HuggingFace: 本地部署,免费但需要 GPU
   - 实际项目可以根据需求切换

4. 向量数据库:
   - Chroma: 轻量级,适合本地开发
   - 生产环境可以考虑: Pinecone, Weaviate, Milvus

5. 性能优化:
   - 单例模式避免重复加载模型
   - 异步写入提升吞吐量
   - 错误日志便于问题定位

⚠️ 注意事项:
-----------
- CrossEncoder 模型较大(~200MB),首次加载较慢
- fetch_k 和 top_k 需要根据实际需求调整
- Chroma DB 文件会随文档量增长,定期清理无用数据
- Windows 下删除文件夹可能遇到权限问题,用 delete_collection 替代

🔗 与其他模块的关系:
-------------------
- graph/nodes/researcher.py: 调用 get_retriever() 执行检索
- api/routes.py: 调用 process_documents() 处理上传的 PDF
- utils/llm.py: Embedding 模型的配置在这里统一管理

📊 典型工作流程:
--------------
用户上传 PDF → routes.upload_files() → process_documents()
                                    ↓
                            PDF → chunks → vectors → Chroma DB
                                    ↓
用户提问 → researcher.research_node() → get_retriever()
                                    ↓
                            query → vectors → similarity search
                                    ↓
                            candidates → rerank → top_k docs
                                    ↓
                            返回给 Writer 生成报告

================================================================================
"""

RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker = None

def get_reranker():
    """
    获取 CrossEncoder 重排序模型(单例模式)
    
    使用单例模式避免重复加载模型,节省内存和初始化时间。
    懒加载设计: 第一次调用时才真正加载模型。
    
    返回:
    - CrossEncoder 实例
    
    异常:
    - RuntimeError: 如果未安装 sentence-transformers 库
    """
    global _reranker
    if _reranker is not None:
        return _reranker
    if CrossEncoder is None:
        raise RuntimeError(
            "未安装 sentence-transformers，无法启用 reranking。请执行：pip install sentence-transformers"
        )
    _reranker = CrossEncoder(RERANKER_MODEL_NAME)
    return _reranker

class RerankRetriever(BaseRetriever):
    """
    两阶段检索器: 向量召回 + CrossEncoder 精排
    
    继承自 LangChain 的 BaseRetriever,实现自定义检索逻辑。
    
    核心属性:
    - vectorstore: Chroma 向量数据库实例
    - reranker: CrossEncoder 重排序模型
    - top_k: 最终返回的文档数量(默认 5)
    - fetch_k: 第一阶段召回的候选数量(默认 20)
    
    工作流程:
    1. 向量相似度搜索: 从 Chroma 召回 fetch_k 个候选文档
    2. CrossEncoder 打分: 对 (query, doc) pair 计算相关性分数
    3. 排序截取: 按分数降序排序,返回 top_k 个文档
    
    优势:
    - 比纯向量检索更准确
    - 比纯 CrossEncoder 更快(先粗排再精排)
    - 平衡了速度和精度
    """

    vectorstore: Any
    reranker: Any
    top_k: int = 5
    fetch_k: int = 20

    def _get_relevant_documents(self, query: str) -> list[Document]:
        """
        核心检索方法: 执行两阶段检索
        
        参数:
        - query: 用户查询字符串
        
        返回:
        - list[Document]: 重排序后的 top_k 个相关文档
        """
        # 1) 先召回更多候选(向量相似度搜索)
        candidates: list[Document] = self.vectorstore.similarity_search(query, k=self.fetch_k)
        if not candidates:
            return []

        # 2) rerank：对 (query, doc_text) 打分(CrossEncoder 精排)
        pairs = [(query, d.page_content) for d in candidates]
        scores = self.reranker.predict(pairs)

        # 3) 按分数排序，取 top_k
        ranked = sorted(zip(candidates, scores), key=lambda x: float(x[1]), reverse=True)
        top_docs = [doc for doc, _ in ranked[: self.top_k]]

        return top_docs

# 定义数据存储路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chroma_db")   # 数据库文件存这里
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads") # 用户上传的 PDF 存这里


#embeddings = HuggingFaceEmbeddings(model_name="moka-ai/m3e-base")
# 这里用的是阿里云的词嵌入模型，需要配置环境变量，不行的话可以用上面的
embeddings = DashScopeEmbeddings(model='text-embedding-v4')

def reset_knowledge_base():
    """
    重置知识库: 清空所有文档和向量索引
    
    用于重新上传文档前的清理工作。
    
    Windows 兼容版修复:
    - 不直接删除 DB 文件夹(避免 WinError 32 文件占用错误)
    - 而是通过 delete_collection() 清空数据
    
    操作流程:
    1. 删除上传目录(uploads/)下的所有 PDF 文件
    2. 重新创建空的 uploads 目录
    3. 清空 Chroma DB 的 collection(保留文件夹结构)
    
    异常处理:
    - 捕获非致命错误,不影响系统继续运行
    """

    if os.path.exists(UPLOAD_DIR):
        try:
            shutil.rmtree(UPLOAD_DIR)
        except Exception as e:
            print(f"--- [RAG] 清理上传目录警告: {e} ---")
    os.makedirs(UPLOAD_DIR, exist_ok=True)


    print("--- [RAG] 正在重置知识库数据... ---")
    try:
        if os.path.exists(DB_PATH):
            vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
            try:
                vectorstore.delete_collection()
                print("--- [RAG] 知识库 Collection 已删除 (数据已清空) ---")
            except Exception:
                pass
    except Exception as e:
        print(f"--- [RAG] 重置数据库时遇到非致命错误 (不影响使用): {e} ---")

def process_documents(file_paths: List[str]):
    """
    核心函数: 文档处理流水线
    
    完整的 RAG 文档处理流程: 读取 → 切片 → 向量化 → 存储
    
    参数:
    - file_paths: PDF 文件路径列表
    
    返回:
    - int: 处理的 chunk 总数
    
    工作流程:
    Step 1: 遍历所有 PDF 文件
            ├─ 使用 PyPDFLoader 加载文档
            ├─ 使用 RecursiveCharacterTextSplitter 切分
            └─ 收集所有 chunk
    
    Step 2: 批量向量化并存储
            ├─ 测试 embedding 性能(ping 测试)
            ├─ 调用 Chroma.from_documents() 写入数据库
            └─ 记录耗时和错误日志
    
    关键配置:
    - chunk_size=500: 每个 chunk 的字符数
    - chunk_overlap=50: chunk 之间的重叠字符数
    - embeddings: DashScopeEmbeddings (阿里云)
    
    异常处理:
    - 单个文件失败不影响其他文件
    - 写入失败时记录详细日志到 upload_error.log
    - 使用 traceback 记录完整堆栈信息
    """
    all_splits = []
    
    for file_path in file_paths:
        print(f"--- [RAG] 正在处理文档: {os.path.basename(file_path)} ---")
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            splits = text_splitter.split_documents(docs)
            all_splits.extend(splits)
        except Exception as e:
            print(f"❌ 处理文件 {file_path} 失败: {e}")
    
    if all_splits:
        print(f"--- [RAG] 正在将 {len(all_splits)} 个片段写入向量数据库... ---")
        print("--- [RAG] split 完成，开始写向量 ---")
        print("--- [RAG] embed 测试开始 ---")
        embed_start = time.time()
        embeddings.embed_documents(["ping"])
        print(f"--- [RAG] embed 测试结束 ({time.time() - embed_start:.2f}s) ---")
        print("--- [RAG] 写入开始 ---")
        # Chroma.from_documents(
        #     documents=all_splits,
        #     embedding=embeddings,
        #     persist_directory=DB_PATH
        # )
        try:
            write_start = time.time()
            Chroma.from_documents(
                documents=all_splits,
                embedding=embeddings,
                persist_directory=DB_PATH
            )
            print(f"--- [RAG] 写入结束 ({time.time() - write_start:.2f}s) ---")
        except Exception as e:
            print(f"--- [RAG] 写入失败: {e!r} ---")
            log_path = os.path.join(BASE_DIR, "upload_error.log")
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write("\n--- CHROMA WRITE ERROR ---\n")
                log_file.write(f"ERROR: {e!r}\n")
                log_file.write(traceback.format_exc())
            raise
                
        print("--- [RAG] 写入完成 ---")
    
    return len(all_splits)

def get_retriever():
    """
    获取检索器: Agent 调用的统一接口
    
    为 Researcher 节点提供标准化的检索服务。
    
    返回:
    - RerankRetriever 实例: 配置好的两阶段检索器
    - None: 如果数据库不存在或为空
    
    配置参数:
    - top_k=5: 最终返回 5 个最相关的文档
    - fetch_k=20: 第一阶段召回 20 个候选
    - reranker: CrossEncoder 重排序模型
    
    使用示例:
    ```python
    retriever = get_retriever()
    if retriever:
        docs = retriever.invoke("用户问题")
        # docs 是重排序后的 top 5 文档
    ```
    """
    if not os.path.exists(DB_PATH) or not os.listdir(DB_PATH):
        return None
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    top_k = 5
    fetch_k = 20
    reranker = get_reranker()
    return RerankRetriever(vectorstore=vectorstore, reranker=reranker, top_k=top_k, fetch_k=fetch_k)

