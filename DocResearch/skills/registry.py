"""
SkillRegistry: 工程化 skill 管理。

提供:
- list_skills() → 列出所有 skill
- get_skill(name) → 返回 skill 的 instructions/rubric/schema
- load_skill_prompt(name) → 返回 instructions.md 内容(供 LLM 使用)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

SKILLS_DIR = Path(__file__).resolve().parent


class SkillRegistry:
    def __init__(self, skills_dir: Path = SKILLS_DIR):
        self.skills_dir = skills_dir

    def list_skills(self) -> List[str]:
        """列出所有 skill 目录名。"""
        return sorted([
            d.name
            for d in self.skills_dir.iterdir()
            if d.is_dir() and (d / "instructions.md").exists()
        ])

    def get_skill(self, name: str) -> Dict[str, Optional[str]]:
        """返回 skill 的 instructions/rubric/schema 内容。"""
        skill_dir = self.skills_dir / name
        if not skill_dir.is_dir():
            raise ValueError(f"Skill not found: {name}")

        result: Dict[str, Optional[str]] = {}

        instructions_path = skill_dir / "instructions.md"
        result["instructions"] = instructions_path.read_text(encoding="utf-8") if instructions_path.exists() else None

        rubric_path = skill_dir / "rubric.yaml"
        result["rubric"] = rubric_path.read_text(encoding="utf-8") if rubric_path.exists() else None

        schema_path = skill_dir / "schema.json"
        result["schema"] = schema_path.read_text(encoding="utf-8") if schema_path.exists() else None

        return result

    def load_skill_prompt(self, name: str) -> str:
        """返回 instructions.md 内容，供 LLM 使用。"""
        skill_dir = self.skills_dir / name
        instructions_path = skill_dir / "instructions.md"
        if not instructions_path.exists():
            raise FileNotFoundError(f"instructions.md not found for skill: {name}")
        return instructions_path.read_text(encoding="utf-8")

    def get_schema(self, name: str) -> Optional[dict]:
        """返回解析后的 schema.json。"""
        skill_dir = self.skills_dir / name
        schema_path = skill_dir / "schema.json"
        if not schema_path.exists():
            return None
        return json.loads(schema_path.read_text(encoding="utf-8"))
