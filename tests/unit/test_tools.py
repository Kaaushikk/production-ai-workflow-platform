import uuid

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from platform_api.agent import plan_tool
from platform_api.models import Base
from platform_api.tools import Tool, ToolContext, ToolError, ToolRegistry


class EmptyArgs(BaseModel):
    model_config = {"extra": "forbid"}


class EchoTool(Tool[EmptyArgs]):
    name = "echo"
    args_model = EmptyArgs

    def run(self, arguments: EmptyArgs, context: ToolContext) -> dict[str, object]:
        return {"tenant_id": str(context.tenant_id)}


def test_registry_rejects_unregistered_tool_and_invalid_arguments() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        context = ToolContext(session, uuid.uuid4())
        registry = ToolRegistry([EchoTool()])

        with pytest.raises(ToolError, match="not allowed"):
            registry.execute("shell", {}, context)
        with pytest.raises(ToolError, match="arguments are invalid"):
            registry.execute("echo", {"unexpected": "value"}, context)


def test_rule_planner_selects_only_known_intents() -> None:
    assert plan_tool("How many documents are indexed?").tool_name == "count_documents"
    assert plan_tool("Find payment recovery policy").tool_name == "search_documents"

