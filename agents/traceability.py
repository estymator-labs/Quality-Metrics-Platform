from .base_agent import BaseAgent


class TraceabilityAgent(BaseAgent):
    """coverage = requirements_with_tests / total_requirements * 100"""

    def run(self) -> dict:
        col = self.collection("requirements")
        all_reqs = list(col.find({}))
        total = len(all_reqs)

        covered = []
        uncovered = []
        for req in all_reqs:
            linked = req.get("linked_test_ids", [])
            entry = {
                "req_id": req.get("req_id"),
                "title": req.get("title"),
                "linked_test_count": len(linked),
            }
            if linked:
                covered.append(entry)
            else:
                uncovered.append(entry)

        coverage = round(len(covered) / total * 100, 2) if total else 0.0

        n = total
        return {
            "metric": "traceability_index",
            "value": coverage,
            "unit": "percent covered",
            "trend": "n/a",
            "trend_delta": 0.0,
            "period": "current",
            "sample_size": n,
            "warning": self.low_sample_warning(n),
            "details": {
                "total_requirements": total,
                "covered_count": len(covered),
                "uncovered_count": len(uncovered),
                "uncovered_requirements": uncovered,
            },
        }
