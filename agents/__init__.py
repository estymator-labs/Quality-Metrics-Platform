from .review_density import ReviewDensityAgent
from .defect_escape import DefectEscapeAgent
from .traceability import TraceabilityAgent
from .risk_closure import RiskClosureAgent
from .soup_completeness import SoupCompletenessAgent

AGENTS = {
    "review_density": ReviewDensityAgent,
    "defect_escape": DefectEscapeAgent,
    "traceability": TraceabilityAgent,
    "risk_closure": RiskClosureAgent,
    "soup_completeness": SoupCompletenessAgent,
}

__all__ = list(AGENTS.keys()) + ["AGENTS"]
