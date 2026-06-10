from .base_agent import BaseAgent


class TraceabilityAgent(BaseAgent):
    """Percentage of requirements covered by tests."""

    def _linked_tests(self, requirement) -> list:
        for field in ("linked_test_ids", "test_ids", "tests", "linked_tests"):
            value = requirement.get(field)
            if isinstance(value, list):
                return value
        return []

    def _is_covered(self, requirement) -> bool:
        if requirement.get("test_covered") is True:
            return True
        return len(self._linked_tests(requirement)) > 0

    def run(self) -> dict:
        col = self.collection("requirements")
        all_reqs = list(col.find({}))
        total = len(all_reqs)

        covered = []
        uncovered = []

        for req in all_reqs:
            linked = self._linked_tests(req)
            entry = {
                "req_id": req.get("req_id") or req.get("requirement_id") or str(req.get("_id")),
                "title": req.get("title") or req.get("description") or "",
                "linked_test_count": len(linked),
            }
            if self._is_covered(req):
                covered.append(entry)
            else:
                uncovered.append(entry)

        coverage = round(len(covered) / total * 100, 2) if total else 0.0

        return {
            "metric": "traceability",
            "value": coverage,
            "unit": "% requirements covered by tests",
            "trend": "not_calculated",
            "trend_delta": None,
            "period": "current",
            "sample_size": total,
            "warning": "No documents found in requirements collection" if total == 0 else self.low_sample_warning(total),
            "details": {
                "total_requirements": total,
                "covered_count": len(covered),
                "uncovered_count": len(uncovered),
                "uncovered_requirements": uncovered,
            },
        }
