from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from app.graph.graph import create_graph
import json
import asyncio
import os
import shutil
import traceback
from app.rag.engine import process_documents, reset_knowledge_base, UPLOAD_DIR
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

"""
================================================================================
【学习指南】routes.py - FastAPI 路由与 SSE 流式响应
================================================================================

📚 核心概念:
这个文件是 IRIS 系统的 API 层,负责:
1. 接收前端请求(上传文档、发起问答)
2. 调用后端服务(RAG 引擎、Agent 工作流)
3. 通过 SSE (Server-Sent Events) 实时推送执行状态

🎯 为什么需要 API 层?
1. 前后端分离: 前端(Vue)和后端(FastAPI)独立部署
2. 标准化接口: RESTful API,便于维护和扩展
3. 流式输出: SSE 让用户体验更流畅,不用等待整个过程完成

💡 类比理解:
想象餐厅的点餐系统:
- 前端(服务员): 接收顾客订单
- API 层(传菜员): 把订单传给厨房,并把进度告诉顾客
- 后端(厨房): 真正做菜的地方(Agent 工作流)
- SSE: 服务员每隔几秒告诉顾客"正在切菜"、"正在炒菜"

🔑 关键组件说明:

1. ChatRequest (Pydantic Model):
   - 定义聊天接口的请求格式
   - query: 用户问题
   - search_mode: "hybrid"(混合) 或 "document"(仅文档)
   - thread_id: 会话 ID,用于多轮对话记忆
   
2. clear_endpoint():
   - 清空知识库接口
   - 调用 reset_knowledge_base()
   - 用于重新上传文档前的清理
   
3. upload_files(files: List[UploadFile]):
   - 批量上传 PDF 文档
   - 限制最多 5 个文件
   - 工作流程:
     Step 1: 重置知识库(reset_knowledge_base)
     Step 2: 保存文件到 uploads/ 目录
     Step 3: 调用 process_documents() 处理文档
     Step 4: 返回处理结果(chunk 数量)
   - 详细日志: 记录每个步骤到 upload_error.log
   
4. chat_endpoint(request: ChatRequest) ⭐ 核心接口:
   - 发起 Agent 工作流执行
   - 使用 SSE 流式推送状态
   - 工作流程:
     Step 1: 初始化 state(query, revision_number=0, search_mode)
     Step 2: 创建 AsyncSqliteSaver(持久化记忆)
     Step 3: 创建 LangGraph 应用(create_graph)
     Step 4: 异步流式执行(app.astream)
     Step 5: 每到一个节点,推送状态更新
     Step 6: 完成后发送 [DONE] 信号

🎓 SSE (Server-Sent Events) 详解:
---------------------------------
什么是 SSE?
- 服务器主动向客户端推送数据的技术
- 基于 HTTP 长连接
- 单向通信(服务器 → 客户端)

为什么用 SSE?
- Agent 工作流耗时长(可能几十秒)
- 传统请求-响应模式会让用户感觉"卡住了"
- SSE 可以实时展示:"正在规划"、"正在检索"、"正在写作"

SSE 格式:
```
data: {"step": "planner", "data": {...}}\n\n
data: {"step": "researcher", "data": {...}}\n\n
data: [DONE]\n\n
```

关键点:
- 每行以 "data: " 开头
- 每条消息以 "\n\n" 结尾(两个换行)
- 前端 EventSource API 自动解析

🔑 chat_endpoint 核心逻辑:

async def event_generator():
  
    SSE 事件生成器
    这是 Python 的异步生成器函数,可以逐个 yield 数据。
    每次 yield 都会立即发送给前端,不需要等待全部完成。

    
    # 1. 初始化状态
    initial_state = {
        "query": request.query, 
        "revision_number": 0,
        "search_mode": request.search_mode 
    }
    
    # 2. 创建持久化记忆(支持多轮对话)
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory:
        # 3. 创建 LangGraph 应用
        app = create_graph(memory=memory)
        
        # 4. 异步流式执行
        async for event in app.astream(initial_state, config=config):
            # event 是一个字典: {"节点名": 状态更新}
            for node_name, state_update in event.items():
                # 5. 序列化成 JSON
                data = json.dumps({"step": node_name, "data": state_update}, ensure_ascii=False)
                # 6. 按照 SSE 格式 yield
                yield f"data: {data}\n\n"
                # 7. 稍微延迟,避免推送太快
                await asyncio.sleep(0.1) 
    
    # 8. 发送结束信号
    yield "data: [DONE]\n\n"

# 9. 返回 StreamingResponse
return StreamingResponse(event_generator(), media_type="text/event-stream")

🎓 学习要点:
-----------
1. Pydantic 数据验证:
   - ChatRequest 自动验证请求格式
   - 类型安全,IDE 支持好
   - 可以添加字段校验(@validator)

2. 异步编程:
   - async/await 提升并发性能
   - AsyncSqliteSaver 支持异步数据库操作
   - astream 是非阻塞的流式执行

3. 上下文管理器:
   - async with 确保资源正确释放
   - 即使发生异常,SQLite 连接也会关闭

4. 错误处理:
   - upload_files 中捕获异常并记录日志
   - 使用 traceback 记录完整堆栈
   - 返回友好的错误信息

5. 日志系统:
   - _log() 函数写入文件日志
   - 便于排查问题和性能分析
   - 生产环境可以用 logging 模块替代

⚠️ 注意事项:
-----------
- thread_id 必须由前端生成并传递(UUID)
- checkpoints.db 会随时间增长,定期清理旧数据
- SSE 不支持双向通信,如果需要客户端反馈要用 WebSocket
- asyncio.sleep(0.1) 避免推送频率过高导致前端卡顿

🔗 与其他模块的关系:
-------------------
- main.py: 注册 router,启动 FastAPI 服务
- graph/graph.py: create_graph() 创建 Agent 工作流
- rag/engine.py: process_documents() 和 reset_knowledge_base()
- frontend/src/services/api.js: 前端调用这些 API

📊 完整请求流程:
--------------
前端用户上传 PDF:
POST /api/upload (files=[pdf1, pdf2])
    ↓
routes.upload_files()
    ↓
reset_knowledge_base() → process_documents()
    ↓
PDF → chunks → vectors → Chroma DB
    ↓
返回: {"status": "success", "chunks_stored": 120}

前端用户发起问答:
POST /api/chat ({query: "...", search_mode: "hybrid", thread_id: "uuid"})
    ↓
routes.chat_endpoint()
    ↓
创建 LangGraph 应用 → astream() 流式执行
    ↓
planner → researcher → writer → reviewer → ...
    ↓
SSE 推送: data: {"step": "planner", "data": {...}}
    ↓
前端实时更新 UI,显示当前进度

================================================================================
"""

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "checkpoints.db")
UPLOAD_LOG_PATH = os.path.join(CURRENT_DIR, "upload_error.log")
router = APIRouter()


class ChatRequest(BaseModel):
    """聊天接口的请求模型,定义前端需要传递的参数"""
    query: str
    search_mode: str = "hybrid" # 默认为混合搜索
    thread_id: str              # 会话 ID,用于多轮对话记忆

@router.post("/clear")
async def clear_endpoint():
    """
    清空知识库接口
    
    删除所有已上传的文档和向量索引,用于重新构建知识库。
    
    返回:
    - {"message": str, "status": str}: 操作结果
    """
    try:
        reset_knowledge_base() 
        return {"message": "知识库已重置", "status": "success"}
    except Exception as e:
        print(f"清空失败: {e}")
        return {"message": f"清空失败: {str(e)}", "status": "error"}

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    批量上传 PDF 文档接口
    
    接收前端上传的 PDF 文件,处理后存入向量数据库。
    
    参数:
    - files: PDF 文件列表(最多 5 个)
    
    返回:
    - status: "success" 或 "error"
    - file_count: 处理的文件数量
    - chunks_stored: 生成的 chunk 总数
    - message: 提示信息
    
    工作流程:
    1. 验证文件数量(≤5)
    2. 重置知识库(清空旧数据)
    3. 保存文件到 uploads/ 目录
    4. 调用 process_documents() 处理
    5. 返回处理结果
    
    异常处理:
    - 超过 5 个文件: 返回 400 错误
    - 处理失败: 记录日志,返回 500 错误
    """

    if len(files) > 5:
        raise HTTPException(status_code=400, detail="一次最多只能上传 5 个文件")

    def _log(line: str) -> None:
        """内部日志函数: 将日志写入文件"""
        with open(UPLOAD_LOG_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")

    try:
        _log("--- UPLOAD START ---")
        _log(f"file_count={len(files)}")

        reset_knowledge_base()
        _log("reset_knowledge_base done")

        saved_paths = []

        for file in files:
            _log(f"saving: {file.filename}")
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(file_path)
            _log(f"saved: {file_path}")

        _log(f"saved_paths={saved_paths}")

        chunks_num = process_documents(saved_paths)
        _log(f"process_documents done chunks={chunks_num}")

        return {
            "status": "success",
            "file_count": len(files),
            "chunks_stored": chunks_num,
            "message": "文档解析完成，知识库构建成功"
        }
    except Exception as e:
        _log(f"ERROR: {e!r}")
        _log(traceback.format_exc())
        print(f"上传处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    核心聊天接口: 发起 Agent 工作流并通过 SSE 流式推送
    
    这是 IRIS 系统最重要的接口,负责:
    1. 接收用户问题
    2. 启动 LangGraph 工作流
    3. 实时推送每个节点的执行状态
    4. 支持多轮对话记忆(thread_id)
    
    参数:
    - request: ChatRequest 对象,包含 query、search_mode、thread_id
    
    返回:
    - StreamingResponse: SSE 流式响应
    
    SSE 事件格式:
    - data: {"step": "planner", "data": {...}}\n\n
    - data: {"step": "researcher", "data": {...}}\n\n
    - data: [DONE]\n\n
    
    工作流程:
    1. 初始化 AgentState
    2. 创建 AsyncSqliteSaver(持久化记忆)
    3. 创建 LangGraph 应用
    4. 异步流式执行(astream)
    5. 每到一个节点,推送状态更新
    6. 完成后发送 [DONE] 信号
    """
    config = {"configurable": {"thread_id": request.thread_id}}
    async def event_generator():
        """
        SSE 事件生成器: 异步生成并推送状态更新
        
        这是一个异步生成器函数,每次 yield 都会立即发送给前端。
        """

        initial_state = {
            "query": request.query, 
            "revision_number": 0,
            "search_mode": request.search_mode 
        }
        
        print(f"🚀 新任务开启 | 模式: {request.search_mode} | 问题: {request.query}")

        async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory:
            app = create_graph(memory=memory)
            
            async for event in app.astream(initial_state, config=config):
                 for node_name, state_update in event.items():
                    data = json.dumps({"step": node_name, "data": state_update}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                    await asyncio.sleep(0.1) 
        
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
