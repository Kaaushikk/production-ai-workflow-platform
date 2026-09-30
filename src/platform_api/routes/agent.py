import uuid
from time import perf_counter

from fastapi import APIRouter, HTTPException, status

from platform_api.agent import plan_tool
from platform_api.auth import TenantDep
from platform_api.dependencies import SessionDep
from platform_api.models import ToolCallRecord
from platform_api.schemas import AgentRequest, AgentResponse
from platform_api.tools import ToolContext, ToolError, default_tool_registry

router = APIRouter(tags=["agent"])


@router.post("/ai/agent", response_model=AgentResponse)
def run_agent(
    request: AgentRequest,
    tenant: TenantDep,
    session: SessionDep,
) -> AgentResponse:
    started = perf_counter()
    plan = plan_tool(request.task)
    run_id = uuid.uuid4()
    try:
        result = default_tool_registry.execute(
            plan.tool_name,
            plan.arguments,
            ToolContext(session=session, tenant_id=tenant.id),
        )
    except ToolError as exc:
        latency_ms = max(0, round((perf_counter() - started) * 1000))
        session.add(
            ToolCallRecord(
                id=run_id,
                tenant_id=tenant.id,
                tool_name=plan.tool_name,
                arguments_json=plan.arguments,
                result_json=None,
                success=False,
                error_code="tool_error",
                latency_ms=latency_ms,
            )
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    latency_ms = max(0, round((perf_counter() - started) * 1000))
    session.add(
        ToolCallRecord(
            id=run_id,
            tenant_id=tenant.id,
            tool_name=plan.tool_name,
            arguments_json=plan.arguments,
            result_json=result,
            success=True,
            error_code=None,
            latency_ms=latency_ms,
        )
    )
    session.commit()
    return AgentResponse(
        run_id=run_id,
        tool_name=plan.tool_name,
        result=result,
        steps=1,
        latency_ms=latency_ms,
    )

