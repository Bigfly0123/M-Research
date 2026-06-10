"""
schemas 包: 全局数据结构定义。

每个模块的输入输出 schema 集中管理，避免 dict 满天飞。
所有 schema 继承 BaseModel，支持校验、序列化和 trace 记录。
"""
