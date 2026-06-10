"""
ingestion 包: 文档加载与结构化切块。

提供 Structure-aware Ingestion 完整能力:
- loaders.py: 文件加载 (Markdown/PDF/TXT)
- structure_parser.py: 结构解析 (heading/code/table/list)
- chunker.py: 切块主入口 (Module 模式)
- metadata.py: 元数据管理 (统计/过滤/导出)
"""
