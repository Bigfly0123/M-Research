"""
LLM 模型工厂: 双模型策略。

fast 模型 (Qwen-Max) 用于生成类任务: 规划、检索、写答案。
smart 模型 (DeepSeek-R1) 用于审查类任务: Judge、Evaluator、Guardrails。
统一入口，各模块通过 get_llm() 获取模型实例。
"""

from langchain_openai import ChatOpenAI
from app.config import config


def get_llm(model_type: str = "fast") -> ChatOpenAI:
    if model_type == "fast":
        return ChatOpenAI(
            model=config.FAST_MODEL,
            temperature=0.7,
            base_url=config.OPENAI_API_BASE,
            api_key=config.OPENAI_API_KEY,
        )
    elif model_type == "smart":
        return ChatOpenAI(
            model=config.SMART_MODEL,
            temperature=0,
            base_url=config.OPENAI_API_BASE,
            api_key=config.OPENAI_API_KEY,
        )
    else:
        raise ValueError(f"Unknown model_type: {model_type}")
