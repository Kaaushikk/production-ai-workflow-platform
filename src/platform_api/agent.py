import re
from dataclasses import dataclass
from typing import Any

UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)


@dataclass(frozen=True)
class ToolPlan:
    tool_name: str
    arguments: dict[str, Any]


def plan_tool(task: str) -> ToolPlan:
    lowered = task.lower()
    if "how many" in lowered or "count" in lowered:
        return ToolPlan("count_documents", {})
    identifier = UUID_PATTERN.search(task)
    if identifier and ("document" in lowered or "metadata" in lowered):
        return ToolPlan("get_document_metadata", {"document_id": identifier.group(0)})
    return ToolPlan("search_documents", {"query": task, "limit": 3})

