from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import re
import yaml


@dataclass
class AgentSpec:
    name: str
    description: str
    prompt: str
    model: str = "inherit"
    tools: str | None = None
    effort: str | None = None
    raw_frontmatter: Dict[str, Any] | None = None
    path: Path | None = None


def parse_agent_markdown(path: str | Path) -> AgentSpec:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Agent file has no YAML frontmatter: {path}")
    frontmatter_text, body = match.groups()
    meta = yaml.safe_load(frontmatter_text) or {}
    if "name" not in meta or "description" not in meta:
        raise ValueError(f"Agent file must include name and description: {path}")
    return AgentSpec(
        name=str(meta["name"]),
        description=str(meta["description"]),
        prompt=body.strip(),
        model=str(meta.get("model", "inherit")),
        tools=str(meta.get("tools")) if meta.get("tools") is not None else None,
        effort=str(meta.get("effort")) if meta.get("effort") is not None else None,
        raw_frontmatter=meta,
        path=path,
    )


def load_agents(agent_dir: str | Path = "agents") -> Dict[str, AgentSpec]:
    agent_dir = Path(agent_dir)
    if not agent_dir.exists():
        raise FileNotFoundError(f"Agent directory not found: {agent_dir}")
    agents: Dict[str, AgentSpec] = {}
    for path in sorted(agent_dir.glob("*.md")):
        spec = parse_agent_markdown(path)
        agents[spec.name] = spec
    return agents


def agent_inventory_markdown(agents: Dict[str, AgentSpec]) -> str:
    rows: List[str] = ["| Agent | Model | Effort | Description |", "|---|---|---|---|"]
    for name, spec in agents.items():
        rows.append(f"| `{name}` | {spec.model} | {spec.effort or '-'} | {spec.description} |")
    return "\n".join(rows)
