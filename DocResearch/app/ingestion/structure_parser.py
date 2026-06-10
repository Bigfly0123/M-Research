"""
Structure Parser: Markdown/PDF 结构化解析器。

核心职责是把原始文档文本拆成带结构信息的元素列表(element)。
每个 element 有 type(heading/code/table/list/text) 和 section_path。
不负责生成 chunk_id 和 contextual_text，这些由 chunker.py 统一处理。
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field


class ParsedElement(BaseModel):
    """解析出的一个结构化元素。"""
    element_type: str = Field(description="heading/code/table/list/text")
    text: str = Field(description="原始文本")
    section_path: List[str] = Field(default_factory=list, description="当前章节层级")
    level: int = Field(default=0, description="标题级别(1-6)，仅 heading 使用")
    language: Optional[str] = Field(default=None, description="代码块语言，仅 code 使用")
    page: Optional[int] = Field(default=None, description="页码，仅 PDF 使用")


def parse_markdown(text: str) -> List[ParsedElement]:
    """解析 Markdown 文本为结构化元素列表。

    逐行扫描，识别 heading/code_block/table/list/paragraph，
    维护 section_stack 跟踪当前章节层级。
    """
    elements = []
    section_stack: List[str] = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # --- Heading ---
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            _update_section_stack(section_stack, level, heading_text)
            elements.append(ParsedElement(
                element_type="heading",
                text=line,
                section_path=list(section_stack),
                level=level,
            ))
            i += 1
            continue

        # --- Code block ---
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip() or None
            code_lines = [line]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                code_lines.append(lines[i])
                i += 1
            elements.append(ParsedElement(
                element_type="code",
                text="\n".join(code_lines),
                section_path=list(section_stack),
                language=lang,
            ))
            continue

        # --- Table (| col | col |) ---
        if "|" in line and i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i + 1]):
            table_lines = [line]
            i += 1
            table_lines.append(lines[i])
            i += 1
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                table_lines.append(lines[i])
                i += 1
            elements.append(ParsedElement(
                element_type="table",
                text="\n".join(table_lines),
                section_path=list(section_stack),
            ))
            continue

        # --- List item (- / * / 1.) ---
        if re.match(r'^(\s*)([-*+]|\d+\.)\s+', line):
            list_lines = [line]
            i += 1
            while i < len(lines) and (re.match(r'^(\s*)([-*+]|\d+\.)\s+', lines[i]) or (lines[i].strip() and lines[i].startswith("  "))):
                list_lines.append(lines[i])
                i += 1
            elements.append(ParsedElement(
                element_type="list",
                text="\n".join(list_lines),
                section_path=list(section_stack),
            ))
            continue

        # --- Empty line ---
        if not line.strip():
            i += 1
            continue

        # --- Normal paragraph ---
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].strip().startswith("```") and not re.match(r'^(\s*)([-*+]|\d+\.)\s+', lines[i]):
            if "|" in lines[i] and i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i + 1]):
                break
            para_lines.append(lines[i])
            i += 1
        elements.append(ParsedElement(
            element_type="text",
            text="\n".join(para_lines),
            section_path=list(section_stack),
        ))

    return elements


def parse_pdf_text(text: str, page: int = None) -> List[ParsedElement]:
    """解析 PDF 页面文本为结构化元素。

    第一版简单处理：按双换行分段，识别可能的标题（短行、全大写等）。
    """
    elements = []
    paragraphs = re.split(r'\n\s*\n', text)

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lines = para.split("\n")
        first_line = lines[0].strip()

        if len(first_line) < 60 and len(lines) == 1 and not first_line.endswith(('.', ',', '。', '，')):
            elements.append(ParsedElement(
                element_type="heading",
                text=first_line,
                section_path=[first_line],
                level=2,
                page=page,
            ))
        else:
            elements.append(ParsedElement(
                element_type="text",
                text=para,
                page=page,
            ))

    return elements


def _update_section_stack(stack: List[str], level: int, heading: str):
    """根据标题级别更新章节栈。"""
    while len(stack) >= level:
        stack.pop()
    stack.append(heading)
