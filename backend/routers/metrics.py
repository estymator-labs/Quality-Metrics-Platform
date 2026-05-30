from fastapi import APIRouter, HTTPException
from agents import AGENTS

router = APIRouter(prefix="/metrics", tags=["metrics"])

AGENT_NAMES = list(AGENTS.keys())


@router.get("/summary")
def metrics_summary():
    """Run all 5 agents and return a combined dashboard JSON."""
    results = {}
    errors = {}
    for name, AgentClass in AGENTS.items():
        try:
            results[name] = AgentClass().run()
        except Exception as exc:
            errors[name] = str(exc)
    return {
        "dashboard": results,
        "errors": errors,
        "agents_available": AGENT_NAMES,
    }


@router.get("/{agent_name}")
def run_agent(agent_name: str):
    """Run a single agent by name and return its metric JSON."""
    AgentClass = AGENTS.get(agent_name)
    if AgentClass is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_name}' not found. Available: {AGENT_NAMES}",
        )
    try:
        return AgentClass().run()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
